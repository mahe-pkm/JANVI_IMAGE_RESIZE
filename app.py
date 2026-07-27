from flask import Flask, jsonify, request, send_file, render_template, abort
from pathlib import Path
import threading
import time
import shutil
import urllib.parse
from PIL import Image

app = Flask(__name__, template_folder='templates', static_folder='static')

import os
import json

BASE_DIR = Path(os.environ.get("BASE_DIR", Path(__file__).resolve().parent))
SRC_DIR = BASE_DIR / "Resizing"
DEST_DIR = BASE_DIR / "Re-sized"
FINAL_DIR = DEST_DIR / "Final For Shopify"

# Ensure directories exist
SRC_DIR.mkdir(parents=True, exist_ok=True)
DEST_DIR.mkdir(parents=True, exist_ok=True)

ACTIVE_DIRS_FILE = BASE_DIR / "active_dirs.json"

def load_active_dirs():
    try:
        if ACTIVE_DIRS_FILE.exists():
            with open(ACTIVE_DIRS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("root_dir", ""), data.get("dest_dir", "")
    except Exception as e:
        print(f"Error loading active dirs: {e}")
    return "", ""

def save_active_dirs(root_dir, dest_dir):
    try:
        with open(ACTIVE_DIRS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"root_dir": str(root_dir), "dest_dir": str(dest_dir)}, f, indent=4)
    except Exception as e:
        print(f"Error saving active dirs: {e}")

last_root_dir, last_dest_dir = load_active_dirs()

# Fallback to defaults if directories do not exist on the current host system
if not last_root_dir or not Path(last_root_dir).exists():
    last_root_dir = str(SRC_DIR.resolve())
if not last_dest_dir or not Path(last_dest_dir).exists():
    last_dest_dir = str(DEST_DIR.resolve())

# Thread-safe logging and status
task_status = {
    "status": "idle",       # "idle", "running", "completed", "failed"
    "task_type": "",        # "audit", "resize", "export"
    "progress": 0,
    "total": 0,
    "current": 0,
    "current_file": "",
    "logs": [],
    "results": None
}
status_lock = threading.RLock()


# PyTorch / Faster R-CNN Model cache
_model = None
_device = None
model_lock = threading.Lock()

def add_log(message):
    with status_lock:
        print(message)
        task_status["logs"].append(message)
        if len(task_status["logs"]) > 500:
            task_status["logs"].pop(0)

def load_cached_model():
    global _model, _device
    with model_lock:
        if _model is None:
            add_log("Loading Faster R-CNN Model...")
            from subject_aware_resize import get_model
            _model, _device = get_model()
            add_log(f"Model successfully loaded on {_device}.")
        return _model, _device

def run_audit_task(root_dir, subfolder):
    global task_status, last_root_dir, last_dest_dir
    try:
        if not root_dir:
            root_path = SRC_DIR
        else:
            root_path = Path(root_dir)
            
        if not root_path.exists() or not root_path.is_dir():
            raise ValueError(f"Root path '{root_path}' does not exist or is not a directory.")
            
        last_root_dir = str(root_path.resolve())
        if root_path.name.lower() == "resizing":
            default_dest = root_path.parent / "Re-sized"
        else:
            default_dest = root_path.parent / f"{root_path.name}_resized"
        last_dest_dir = str(default_dest.resolve())
        save_active_dirs(last_root_dir, last_dest_dir)
            
        search_dir = root_path / subfolder if subfolder else root_path
        image_paths = []
        for ext in ['*.png', '*.jpg', '*.jpeg']:
            image_paths.extend(list(search_dir.rglob(ext)))
            
        total = len(image_paths)
        with status_lock:
            task_status["status"] = "running"
            task_status["task_type"] = "audit"
            task_status["progress"] = 0
            task_status["total"] = total
            task_status["current"] = 0
            task_status["logs"] = []
            task_status["results"] = None
            
        add_log(f"Starting audit for {total} images under {search_dir}...")
        
        model, device = load_cached_model()
        from analyze_padding import needs_padding
        from subject_aware_resize import get_subject_bbox
        
        pad_count = 0
        normal_crop_count = 0
        
        for i, img_path in enumerate(image_paths):
            try:
                rel_path = img_path.relative_to(root_path)
            except Exception:
                rel_path = img_path
            rel_path_str = str(rel_path)
            
            with status_lock:
                if task_status["status"] == "idle":
                    add_log("Audit cancelled by user.")
                    return
                task_status["current"] = i + 1
                task_status["progress"] = int((i + 1) / total * 100)
                task_status["current_file"] = rel_path_str
                
            try:
                with Image.open(img_path).convert("RGB") as img:
                    bbox = get_subject_bbox(model, device, img)
                    if needs_padding(img, bbox):
                        pad_count += 1
                        add_log(f"[{i+1}/{total}] PADDING REQUIRED: {rel_path_str}")
                    else:
                        normal_crop_count += 1
                        add_log(f"[{i+1}/{total}] Crop ready: {rel_path_str}")
            except Exception as e:
                add_log(f"Error on {img_path.name}: {e}")
                
        add_log("--- Audit Complete ---")
        add_log(f"Total Processed: {total}")
        add_log(f"Images requiring padding: {pad_count}")
        add_log(f"Images crop ready: {normal_crop_count}")
        
        with status_lock:
            task_status["status"] = "completed"
            task_status["results"] = {
                "total": total,
                "padding_required": pad_count,
                "crop_ready": normal_crop_count
            }
            
    except Exception as exc:
        add_log(f"Audit task failed: {exc}")
        with status_lock:
            task_status["status"] = "failed"

def run_resize_task(root_dir, dest_dir, subfolder):
    global task_status, last_root_dir, last_dest_dir
    try:
        if not root_dir:
            root_path = SRC_DIR
        else:
            root_path = Path(root_dir)
            
        if not root_path.exists() or not root_path.is_dir():
            raise ValueError(f"Root path '{root_path}' does not exist or is not a directory.")
            
        if not dest_dir:
            if root_path.name.lower() == "resizing":
                dest_dir_path = root_path.parent / "Re-sized"
            else:
                dest_dir_path = root_path.parent / f"{root_path.name}_resized"
        else:
            dest_dir_path = Path(dest_dir)
            
        last_root_dir = str(root_path.resolve())
        last_dest_dir = str(dest_dir_path.resolve())
        save_active_dirs(last_root_dir, last_dest_dir)
            
        search_dir = root_path / subfolder if subfolder else root_path
        image_paths = []
        for ext in ['*.png', '*.jpg', '*.jpeg']:
            image_paths.extend(list(search_dir.rglob(ext)))
            
        total = len(image_paths)
        with status_lock:
            task_status["status"] = "running"
            task_status["task_type"] = "resize"
            task_status["progress"] = 0
            task_status["total"] = total
            task_status["current"] = 0
            task_status["logs"] = []
            task_status["results"] = None
            
        add_log(f"Starting resizing for {total} images under {search_dir}...")
        add_log(f"Output directory: {dest_dir_path}")
        
        model, device = load_cached_model()
        from subject_aware_resize import get_subject_bbox, smart_crop_and_resize
        
        padded_files = []
        
        for i, img_path in enumerate(image_paths):
            rel_path = img_path.relative_to(root_path)
            dest_path = dest_dir_path / rel_path
            
            rel_path_str = str(rel_path)
            
            with status_lock:
                if task_status["status"] == "idle":
                    add_log("Resizing cancelled by user.")
                    return
                task_status["current"] = i + 1
                task_status["progress"] = int((i + 1) / total * 100)
                task_status["current_file"] = rel_path_str
                
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                with Image.open(img_path).convert("RGB") as img:
                    bbox = get_subject_bbox(model, device, img)
                    result_img, used_pad = smart_crop_and_resize(img, bbox)
                    result_img.save(dest_path)
                    if used_pad:
                        padded_files.append(rel_path)
                        add_log(f"[{i+1}/{total}] PADDED (blur fill): {rel_path_str}")
                    else:
                        add_log(f"[{i+1}/{total}] Cropped: {rel_path_str}")
            except Exception as e:
                add_log(f"Error on {img_path.name}: {e}")
                
        # Update manual_patch_list.md
        list_path = dest_dir_path / "manual_patch_list.md"
        existing_items = set()
        if list_path.exists():
            with open(list_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("- `") and line.endswith("`"):
                        item = line[3:-1]
                        existing_items.add(item.replace('/', '\\'))
                        
        for p in padded_files:
            existing_items.add(str(p).replace('/', '\\'))
            
        with open(list_path, "w", encoding="utf-8") as f:
            f.write("# Images Requiring Manual Patch (Padded)\n\n")
            for item in sorted(list(existing_items)):
                f.write(f"- `{item}`\n")
                
        add_log("--- Resizing Complete ---")
        add_log(f"Total Processed: {total}")
        add_log(f"New padded files logged: {len(padded_files)}")
        
        with status_lock:
            task_status["status"] = "completed"
            task_status["results"] = {
                "total": total,
                "new_padded": len(padded_files)
            }
            
    except Exception as exc:
        add_log(f"Resize task failed: {exc}")
        with status_lock:
            task_status["status"] = "failed"

def run_export_task(export_src, export_dest):
    global task_status
    try:
        if not export_src:
            export_src_path = DEST_DIR / "With Logo"
        else:
            export_src_path = Path(export_src)
            
        if not export_dest:
            export_dest_path = DEST_DIR / "Final For Shopify"
        else:
            export_dest_path = Path(export_dest)
            
        from move_to_shopify import get_export_folders
        folders = get_export_folders(export_src_path)
        total = len(folders)
        
        with status_lock:
            task_status["status"] = "running"
            task_status["task_type"] = "export"
            task_status["progress"] = 0
            task_status["total"] = total
            task_status["current"] = 0
            task_status["logs"] = []
            task_status["results"] = None
            
        add_log(f"Starting Shopify export from {export_src_path} to {export_dest_path}...")
        
        import re
        class ProgressLogger:
            def __init__(self):
                self.current_folder_count = 0
                
            def log(self, message):
                add_log(message)
                if "Processing folder" in message:
                    self.current_folder_count += 1
                    with status_lock:
                        task_status["current"] = self.current_folder_count
                        if total > 0:
                            task_status["progress"] = int((self.current_folder_count) / total * 100)
                        match = re.search(r"Processing folder '([^']+)'", message)
                        if match:
                            task_status["current_file"] = match.group(1)
                            
        logger = ProgressLogger()
        from move_to_shopify import run_export
        copied_count = run_export(
            src_dir=str(export_src_path),
            dest_dir=str(export_dest_path),
            dry_run=False,
            delete_empty_src=True,
            log_callback=logger.log
        )
        
        add_log("--- Export Complete ---")
        add_log(f"Successfully copied and renamed {copied_count} files to Final For Shopify directory.")
        
        with status_lock:
            task_status["status"] = "completed"
            task_status["results"] = {
                "moved_folders": total,
                "copied_files": copied_count
            }
            
    except Exception as exc:
        add_log(f"Export task failed: {exc}")
        with status_lock:
            task_status["status"] = "failed"


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
            # 1. Look for subfolders
            for p in sorted(root_path.iterdir()):
                if p.is_dir() and not p.name.startswith('.'):
                    img_count = len(list(p.rglob('*.png')) + list(p.rglob('*.jpg')) + list(p.rglob('*.jpeg')) + list(p.rglob('*.PNG')) + list(p.rglob('*.JPG')) + list(p.rglob('*.JPEG')))
                    if img_count > 0:
                        folders.append({
                            "name": p.name,
                            "image_count": img_count
                        })
            
            # 2. Count images directly in the root
            root_img_count = len(list(root_path.glob('*.png')) + list(root_path.glob('*.jpg')) + list(root_path.glob('*.jpeg')) + list(root_path.glob('*.PNG')) + list(root_path.glob('*.JPG')) + list(root_path.glob('*.JPEG')))
            if root_img_count > 0:
                folders.append({
                    "name": ".",
                    "image_count": root_img_count
                })
            
            # 3. If there are no subfolders and no direct files, check if there are any images recursively
            if not folders:
                all_img_count = len(list(root_path.rglob('*.png')) + list(root_path.rglob('*.jpg')) + list(root_path.rglob('*.jpeg')) + list(root_path.rglob('*.PNG')) + list(root_path.rglob('*.JPG')) + list(root_path.rglob('*.JPEG')))
                if all_img_count > 0:
                    folders.append({
                        "name": ".",
                        "image_count": all_img_count
                    })
            
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
        return jsonify(task_status)

@app.route('/api/active-directory', methods=['GET'])
def get_active_directory():
    global last_root_dir, last_dest_dir
    return jsonify({
        "root_dir": last_root_dir,
        "dest_dir": last_dest_dir
    })

@app.route('/api/select-folder', methods=['GET'])
def select_folder():
    initial_dir = request.args.get('initial_dir', '').strip()
    try:
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cancel', methods=['POST'])
def cancel_task():
    with status_lock:
        if task_status["status"] == "running":
            task_status["status"] = "idle"
            add_log("Task cancellation requested.")
            return jsonify({"message": "Cancellation requested."})
        return jsonify({"message": "No task is currently running."})

@app.route('/api/analyze', methods=['POST'])
def start_analyze():
    data = request.json or {}
    folder = data.get('folder', '')
    root_dir = data.get('root_dir', '').strip()
    
    with status_lock:
        if task_status["status"] == "running":
            return jsonify({"error": "A task is already running."}), 400
            
    threading.Thread(target=run_audit_task, args=(root_dir, folder)).start()
    return jsonify({"message": "Audit started."})

@app.route('/api/resize', methods=['POST'])
def start_resize():
    data = request.json or {}
    folder = data.get('folder', '')
    root_dir = data.get('root_dir', '').strip()
    dest_dir = data.get('dest_dir', '').strip()
    
    with status_lock:
        if task_status["status"] == "running":
            return jsonify({"error": "A task is already running."}), 400
            
    threading.Thread(target=run_resize_task, args=(root_dir, dest_dir, folder)).start()
    return jsonify({"message": "Resizing started."})

@app.route('/api/export', methods=['POST'])
def start_export():
    data = request.json or {}
    export_src = data.get('export_src', '').strip()
    export_dest = data.get('export_dest', '').strip()
    
    with status_lock:
        if task_status["status"] == "running":
            return jsonify({"error": "A task is already running."}), 400
            
    threading.Thread(target=run_export_task, args=(export_src, export_dest)).start()
    return jsonify({"message": "Export started."})

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
                            "resized_url": resized_url
                        })
        return jsonify({"items": items})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

if __name__ == '__main__':
    print("Starting server on http://127.0.0.1:5000")
    app.run(debug=False, port=5000)
