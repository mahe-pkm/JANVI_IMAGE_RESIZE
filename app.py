from flask import Flask, jsonify, request, send_file, render_template, abort
from pathlib import Path
import json
import os
import subprocess
import threading
import urllib.parse
import io
from jobs import Jobs
from photoshop_repair import repair_status, SCRIPT
from processing import images_under, run_images, run_export, export_plan, export_signature, validate_paths
from logo_processing import (DEFAULTS, asset_path, list_assets, list_presets, read_logo,
                             render, run_logo, save_asset, save_preset, settings_for, source_image)
from hardware import inventory
from telemetry import Telemetry

APP_DIR = Path(__file__).resolve().parent
BASE_DIR = Path(os.environ.get("BASE_DIR", APP_DIR / "data")).resolve()
BASE_DIR.mkdir(parents=True, exist_ok=True)
SRC_DIR = BASE_DIR / "Resizing"
DEST_DIR = BASE_DIR / "Re-sized"
SRC_DIR.mkdir(exist_ok=True)
DEST_DIR.mkdir(exist_ok=True)
ACTIVE_DIRS_FILE = BASE_DIR / "active_dirs.json"
app = Flask(__name__, template_folder=str(APP_DIR / "templates"), static_folder=str(APP_DIR / "static"))
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024
jobs = Jobs(BASE_DIR / 'job-logs')
status_lock = jobs.lock
telemetry = Telemetry()
logo_store_lock = threading.Lock()
folder_picker_lock = threading.Lock()
last_root_dir, last_dest_dir = str(SRC_DIR), str(DEST_DIR)
try:
    saved = json.loads(ACTIVE_DIRS_FILE.read_text(encoding="utf-8"))
    if Path(saved.get("root_dir", "")).is_dir():
        last_root_dir = saved["root_dir"]
        last_dest_dir = saved.get("dest_dir", str(DEST_DIR))
except (OSError, ValueError):
    pass

@app.before_request
def local_mutations_only():
    if request.method == "POST":
        origin = request.headers.get("Origin")
        if origin and origin != request.host_url.rstrip("/"):
            abort(403, "Only the local dashboard can start operations.")

@app.get("/api/health")
def health():
    return jsonify({"app": "janvi-image-resize", "version": "0.2.0", "ready": True})

@app.get("/api/devices")
def devices():
    return jsonify({"devices": inventory()})

@app.get("/api/telemetry")
def utilization():
    return jsonify(telemetry.snapshot())

@app.get("/api/logo/assets")
def logo_assets():
    return jsonify({"assets": list_assets(BASE_DIR), "defaults": DEFAULTS})

@app.post("/api/logo/assets")
def upload_logo():
    try:
        with logo_store_lock:
            item = save_asset(BASE_DIR, request.files.get("file"))
        return jsonify(item), 201
    except (ValueError, OSError) as exc:
        return jsonify({"error": str(exc)}), 400

@app.route("/api/logo/presets", methods=["GET", "POST"])
def logo_presets():
    try:
        with logo_store_lock:
            if request.method == "POST":
                data = request.get_json(silent=True) or {}
                item = save_preset(BASE_DIR, data.get("name"), data.get("asset_id"), data.get("settings", {}))
                return jsonify(item), 201
            return jsonify({"presets": list_presets(BASE_DIR)})
    except (ValueError, OSError) as exc:
        return jsonify({"error": str(exc)}), 400

@app.get("/api/logo/images")
def logo_images():
    try:
        root = Path(request.args.get("root", "")).resolve()
        if not request.args.get("root") or not root.is_dir():
            raise ValueError("Choose an existing folder of resized images.")
        files = images_under(root)
        return jsonify({"images": [p.relative_to(root).as_posix() for p in files[:500]], "total": len(files)})
    except (ValueError, OSError) as exc:
        return jsonify({"error": str(exc)}), 400

@app.post("/api/logo/preview")
def logo_preview():
    data = request.get_json(silent=True) or {}
    try:
        image_path = source_image(data.get("source", ""), data.get("image", ""))
        logo = read_logo(asset_path(BASE_DIR, data.get("asset_id", "default")))
        result, _ = render(image_path, logo, data.get("settings", {}))
        buffer = io.BytesIO()
        result.save(buffer, format="PNG")
        buffer.seek(0)
        return send_file(buffer, mimetype="image/png", max_age=0)
    except (ValueError, OSError) as exc:
        return jsonify({"error": str(exc)}), 400

@app.post("/api/logo/apply")
def logo_apply():
    data = request.get_json(silent=True) or {}
    try:
        source = data.get("source", "")
        destination = data.get("destination", "")
        if not source or not destination:
            raise ValueError("Choose both source and output folders.")
        validate_paths(source, destination)
        if 'target_width' in data or 'target_height' in data:
            width, height = data.get('target_width'), data.get('target_height')
            if type(width) is not int or type(height) is not int or not (64 <= width <= 6000 and 64 <= height <= 6000) or width * height > 24000000:
                raise ValueError('Choose valid output dimensions before logo placement.')
            from PIL import Image, ImageOps
            for file in images_under(Path(source)):
                with Image.open(file) as original:
                    actual = ImageOps.exif_transpose(original).size
                if actual != (width, height):
                    raise ValueError(f'{file.name} is {actual[0]} × {actual[1]}. Run Resize to prepare {width} × {height} before placing the logo.')
        asset_id = data.get("asset_id", "default")
        read_logo(asset_path(BASE_DIR, asset_id))
        settings = settings_for(data.get("settings", {}))
        job_id = jobs.start("logo", lambda job: run_logo(job, BASE_DIR, source, destination, asset_id, settings))
        return jsonify({"message": "Logo placement started.", "job_id": job_id}), 202
    except (ValueError, OSError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 409 if jobs.snapshot()["active"] else 400

# REST API endpoints

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/browse', methods=['GET'])
def browse_directory():
    path_str = request.args.get('path', '').strip()
    try:
        if not path_str:
            path = BASE_DIR
        else:
            path = Path(path_str).resolve()
            
        if not path.exists() or not path.is_dir():
            return jsonify({"error": "Path does not exist or is not a directory"}), 400
            
        dirs = []
        for p in sorted(path.iterdir()):
            try:
                if p.is_dir() and not p.name.startswith('.'):
                    dirs.append(p.name)
            except PermissionError:
                pass
                
        parent_path = str(path.parent) if path.parent != path else ""
        return jsonify({
            "current_path": str(path),
            "parent_path": parent_path,
            "dirs": dirs
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/folders', methods=['GET'])
def get_folders():
    try:
        root_dir = request.args.get('root_dir', '').strip()
        if not root_dir:
            root_path = SRC_DIR
        else:
            root_path = Path(root_dir)
            
        folders = []
        if root_path.exists() and root_path.is_dir():
            for child in sorted(root_path.iterdir()):
                if child.is_dir() and not child.name.startswith('.'):
                    count = len(images_under(child))
                    if count:
                        folders.append({"name": child.name, "image_count": count})
            direct = len(images_under(root_path, recursive=False))
            if direct:
                folders.append({"name": ".", "image_count": direct})
            return jsonify({
                "folders": folders, 
                "valid": True, 
                "resolved_path": str(root_path.resolve())
            })
        else:
            return jsonify({
                "folders": [], 
                "valid": False, 
                "error": f"Path '{root_dir}' is not an active directory."
            })
    except Exception as e:
        return jsonify({"error": str(e), "valid": False}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    with status_lock:
        return jsonify(jobs.snapshot(request.args.get("after", 0, type=int)))

@app.route('/api/active-directory', methods=['GET'])
def get_active_directory():
    global last_root_dir, last_dest_dir
    return jsonify({"root_dir": last_root_dir, "dest_dir": last_dest_dir,
                    "export_src": str(DEST_DIR / "With Logo"), "export_dest": str(DEST_DIR / "Final For Shopify")})

@app.route('/api/select-folder', methods=['POST'])
def select_folder():
    initial_dir = (request.get_json(silent=True) or {}).get('initial_dir', '')
    if not isinstance(initial_dir, str):
        return jsonify({"error": "Invalid initial folder."}), 400
    initial_dir = initial_dir.strip()
    if not folder_picker_lock.acquire(blocking=False):
        return jsonify({"error": "A folder picker is already open."}), 409
    try:
        if os.name == 'nt':
            powershell = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe'
            args = [str(powershell), '-NoProfile', '-NonInteractive', '-STA', '-ExecutionPolicy', 'Bypass',
                    '-File', str(APP_DIR / 'select_folder.ps1')]
            if initial_dir and Path(initial_dir).is_dir():
                args += ['-InitialDirectory', initial_dir]
            result = subprocess.run(args, capture_output=True, encoding='utf-8', errors='replace',
                                    creationflags=subprocess.CREATE_NO_WINDOW, check=True)
            selected = json.loads(result.stdout)['selected_path']
            return jsonify({"selected_path": str(Path(selected).resolve()) if selected else ''})
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        
        # If initial_dir is empty or invalid, default to BASE_DIR
        if not initial_dir or not Path(initial_dir).exists():
            initial_dir = str(BASE_DIR)
            
        selected_dir = filedialog.askdirectory(
            initialdir=initial_dir,
            title="Select Folder"
        )
        root.destroy()
        
        if selected_dir:
            normalized_path = str(Path(selected_dir).resolve())
            return jsonify({"selected_path": normalized_path})
        else:
            return jsonify({"selected_path": ""})
    except Exception:
        app.logger.exception('Folder picker failed')
        return jsonify({"error": "Could not open the system folder picker. Enter the folder path manually."}), 500
    finally:
        folder_picker_lock.release()

@app.post("/api/cancel")
def cancel_task():
    return jsonify({"message": "Cancellation requested; finishing the current operation." if jobs.cancel() else "No active task."})

@app.post('/api/export/preview')
def preview_export():
    data = request.get_json(silent=True) or {}
    try:
        source, destination, mode = data.get('export_src'), data.get('export_dest'), data.get('mode')
        if not isinstance(source, str) or not source.strip() or not isinstance(destination, str) or not destination.strip():
            raise ValueError('Choose a source folder and a separate output folder.')
        resolved_source, resolved_destination, entries = export_plan(source.strip(), destination.strip(), mode)
        return jsonify({'total': len(entries), 'copy': sum(e['status'] == 'copy' for e in entries),
                        'already_present': sum(e['status'] == 'already_present' for e in entries),
                        'conflicts': sum(e['status'] == 'conflict' for e in entries), 'entries': entries[:200],
                        'signature': export_signature(resolved_source, resolved_destination, mode, entries)})
    except (ValueError, OSError, TypeError) as exc:
        return jsonify({'error': str(exc)}), 400

@app.post("/api/analyze")
@app.post("/api/resize")
@app.post("/api/export")
def start_operation():
    global last_root_dir, last_dest_dir
    data = request.get_json(silent=True) or {}
    kind = {"analyze": "audit", "resize": "resize", "export": "export"}[request.path.rsplit("/", 1)[-1]]
    try:
        if kind == "export":
            source = data.get("export_src")
            destination = data.get("export_dest")
            mode = data.get('mode')
            signature = data.get('signature')
            if not isinstance(source, str) or not source.strip() or not isinstance(destination, str) or not destination.strip():
                raise ValueError('Choose a source folder and a separate output folder.')
            if mode not in {'lightroom', 'native'}:
                raise ValueError('Choose Lightroom or native app export.')
            if not isinstance(signature, str) or len(signature) != 64:
                raise ValueError('Preview the export before starting it.')
            validate_paths(source, destination)
            target = lambda job: run_export(job, source, destination, mode, signature)
        else:
            source = data.get("root_dir") or str(SRC_DIR)
            destination = data.get("dest_dir") or str(Path(source).with_name("Re-sized" if Path(source).name.lower() == "resizing" else Path(source).name + "_resized"))
            folder = data.get("folder", "")
            validate_paths(source, destination, folder)
            device = data.get("device_id", "cpu")
            width, height = data.get('target_width', 1200), data.get('target_height', 1800)
            if type(width) is not int or type(height) is not int or not (64 <= width <= 6000 and 64 <= height <= 6000) or width * height > 24000000:
                raise ValueError('Choose whole-number output dimensions from 64 to 6000 pixels, up to 24 megapixels.')
            target = lambda job: run_images(job, kind, source, destination, folder, device, width, height)
        job_id = jobs.start(kind, target, device_id=data.get("device_id", "cpu") if kind != "export" else "cpu")
        if kind != "export":
            last_root_dir, last_dest_dir = str(Path(source).resolve()), str(Path(destination).resolve())
            try:
                ACTIVE_DIRS_FILE.write_text(json.dumps({"root_dir": last_root_dir, "dest_dir": last_dest_dir}), encoding="utf-8")
            except OSError as exc:
                jobs.log(f"Settings could not be saved: {exc}")
        return jsonify({"message": f"{kind.title()} started.", "job_id": job_id}), 202
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 409 if jobs.snapshot()["active"] else 400

@app.route('/api/patch-list', methods=['GET'])
def get_patch_list():
    try:
        root_dir = request.args.get('root_dir', '').strip()
        dest_dir = request.args.get('dest_dir', '').strip()
        
        if not root_dir:
            root_path = SRC_DIR
        else:
            root_path = Path(root_dir)
            
        if not dest_dir:
            if root_path.name.lower() == "resizing":
                dest_dir_path = root_path.parent / "Re-sized"
            else:
                dest_dir_path = root_path.parent / f"{root_path.name}_resized"
        else:
            dest_dir_path = Path(dest_dir)
            
        list_path = dest_dir_path / "manual_patch_list.md"
        items = []
        if list_path.exists():
            with open(list_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("- `") and line.endswith("`"):
                        path_str = line[3:-1]
                        path_forward = path_str.replace('\\', '/')
                        
                        src_root = str(root_path.resolve())
                        dest_root = str(dest_dir_path.resolve())
                        
                        src_url = f"/api/image?root={urllib.parse.quote(src_root)}&file={urllib.parse.quote(path_forward)}"
                        resized_url = f"/api/image?root={urllib.parse.quote(dest_root)}&file={urllib.parse.quote(path_forward)}"
                        
                        items.append({
                            "relative_path": path_str,
                            "src_url": src_url,
                            "resized_url": resized_url,
                            "padded": True
                        })
        padded_count = len(items)
        if request.args.get('all') == '1' and dest_dir_path.is_dir():
            padded_names = {item['relative_path'].replace('\\', '/') for item in items}
            items = []
            for file in images_under(dest_dir_path):
                relative = file.relative_to(dest_dir_path.resolve()).as_posix()
                source_file = (root_path / relative).resolve()
                if not source_file.is_relative_to(root_path.resolve()) or not source_file.is_file():
                    continue
                items.append({'relative_path': relative, 'padded': relative in padded_names,
                              'src_url': f"/api/image?root={urllib.parse.quote(str(root_path.resolve()))}&file={urllib.parse.quote(relative)}",
                              'resized_url': f"/api/image?root={urllib.parse.quote(str(dest_dir_path.resolve()))}&file={urllib.parse.quote(relative)}"})
        return jsonify({"items": items, "padded_count": padded_count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get('/api/photoshop/status')
def photoshop_status():
    try:
        return jsonify(repair_status(request.args.get('dest_dir') or last_dest_dir))
    except (OSError, ValueError, KeyError) as exc:
        return jsonify(error=str(exc)), 400


@app.get('/api/photoshop/script')
def photoshop_script():
    destination = Path(request.args.get('dest_dir') or last_dest_dir).resolve()
    script = destination / SCRIPT
    if not script.is_file():
        return jsonify(error='No generated Photoshop script. Complete resizing first.'), 404
    return send_file(script, as_attachment=True, download_name=SCRIPT)


@app.route('/api/image')
def serve_image():
    root = request.args.get('root', '').strip()
    file = request.args.get('file', '').strip()
    
    if not root or not file:
        abort(400, "Missing root or file parameter")
        
    try:
        root_path = Path(root).resolve()
        full_path = (root_path / file).resolve()
    except Exception:
        abort(400, "Invalid path structure")
        
    # Prevent path traversal outside allowed root
    if not full_path.is_relative_to(root_path):
        abort(403, "Access denied: outside allowed root directory")
        
    if not full_path.exists() or not full_path.is_file():
        abort(404, "Image not found")
        
    return send_file(full_path)

if __name__ == "__main__":
    from waitress import serve
    serve(app, host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")), threads=6)
