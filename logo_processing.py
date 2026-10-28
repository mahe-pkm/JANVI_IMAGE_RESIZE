"""Logo assets, matching preview and source-preserving batch composition."""
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import uuid

from PIL import Image, ImageOps
from processing import images_under, validate_paths, copy_folder_structure

APP_DIR = Path(__file__).resolve().parent
DEFAULT_LOGO = APP_DIR / "assets" / "default-logo.png"
POSITIONS = {f"{vertical}-{horizontal}" for vertical in ("top", "middle", "bottom")
             for horizontal in ("left", "center", "right")}
DEFAULTS = {"position": "top-left", "width_pct": 15.0,
            "opacity_pct": 88.1, "offset_x_pct": 0.0, "offset_y_pct": 0.0, "rotation": 0,
            "size_mode": "proportional"}
MAX_ASSET_BYTES = 10 * 1024 * 1024


def settings_for(raw):
    if not isinstance(raw, dict):
        raise ValueError("Invalid logo settings.")
    result = {"position": raw.get("position", DEFAULTS["position"])}
    if result["position"] not in POSITIONS:
        raise ValueError("Choose a valid logo position.")
    result["size_mode"] = raw.get("size_mode", DEFAULTS["size_mode"])
    if result["size_mode"] not in {"proportional", "fit", "fill"}:
        raise ValueError("Choose Proportional, Fit, or Fill.")
    rotation = raw.get("rotation", 0)
    try:
        rotation = float(rotation)
    except (TypeError, ValueError):
        raise ValueError("Choose a valid logo rotation.") from None
    if rotation not in (0, 90, 180, 270):
        raise ValueError("Logo rotation must be 0, 90, 180, or 270 degrees.")
    result["rotation"] = int(rotation)
    for key, lower, upper in (("width_pct", 1, 60), ("opacity_pct", 0, 100),
                              ("offset_x_pct", 0, 40), ("offset_y_pct", 0, 40)):
        try:
            value = float(raw.get(key, DEFAULTS[key]))
        except (ValueError, TypeError):
            raise ValueError(f"Invalid {key} value.") from None
        if not math.isfinite(value) or not lower <= value <= upper:
            raise ValueError(f"{key} must be between {lower} and {upper}.")
        result[key] = value
    return result


def asset_path(base, asset_id):
    if asset_id == "default":
        path = DEFAULT_LOGO
    elif isinstance(asset_id, str) and re.fullmatch(r"[0-9a-f]{64}", asset_id):
        path = Path(base) / "logos" / f"{asset_id}.png"
    else:
        raise ValueError("Choose a saved logo.")
    if not path.is_file():
        raise ValueError("The selected logo is unavailable. Choose or upload it again.")
    return path


def read_logo(path):
    with Image.open(path) as source:
        if source.format not in {"PNG", "WEBP"}:
            raise ValueError("Use a PNG or WebP logo.")
        if source.width * source.height > 20_000_000:
            raise ValueError("The logo image is too large.")
        logo = ImageOps.exif_transpose(source).convert("RGBA")
    bounds = logo.getchannel("A").getbbox()
    if not bounds:
        raise ValueError("The logo is fully transparent.")
    return logo


def save_asset(base, file):
    if not file or not file.filename:
        raise ValueError("Choose a PNG, JPG, or WebP logo file.")
    raw = file.stream.read(MAX_ASSET_BYTES + 1)
    if len(raw) > MAX_ASSET_BYTES:
        raise ValueError("Logo files must be 10 MB or smaller.")
    try:
        with Image.open(io.BytesIO(raw)) as source:
            if source.format not in {"PNG", "WEBP", "JPEG"}:
                raise ValueError("Use a PNG, JPG, or WebP logo.")
            if source.width * source.height > 20_000_000:
                raise ValueError("The logo image is too large.")
            logo = ImageOps.exif_transpose(source).convert("RGBA")
            if not logo.getchannel("A").getbbox():
                raise ValueError("The logo is fully transparent.")
    except (OSError, SyntaxError) as exc:
        raise ValueError("Could not open the logo image.") from exc
    # Normalized lossless PNG makes uploaded assets portable and self-contained.
    out = io.BytesIO()
    logo.save(out, format="PNG")
    content = out.getvalue()
    identity = hashlib.sha256(content).hexdigest()
    folder = Path(base) / "logos"
    folder.mkdir(parents=True, exist_ok=True)
    image_path = folder / f"{identity}.png"
    if not image_path.exists():
        temp = folder / f".{uuid.uuid4().hex}.tmp"
        try:
            temp.write_bytes(content)
            os.replace(temp, image_path)
        finally:
            temp.unlink(missing_ok=True)
    label = Path(file.filename.replace("\\", "/")).name[:120] or "Uploaded logo"
    metadata = folder / f"{identity}.json"
    if not metadata.exists():
        metadata.write_text(json.dumps({"name": label}, ensure_ascii=False), encoding="utf-8")
    return {"id": identity, "name": label}


def list_assets(base):
    items = [{"id": "default", "name": "Janvi logo (included)"}] if DEFAULT_LOGO.is_file() else []
    folder = Path(base) / "logos"
    if folder.is_dir():
        for path in sorted(folder.glob("*.png")):
            if not re.fullmatch(r"[0-9a-f]{64}", path.stem):
                continue
            try:
                label = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))["name"]
            except (OSError, ValueError, KeyError):
                label = "Saved logo " + path.stem[:8]
            items.append({"id": path.stem, "name": label})
    return items


def presets_path(base):
    return Path(base) / "logo-presets.json"


def list_presets(base):
    path = presets_path(base)
    if not path.exists():
        return []
    try:
        items = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            raise ValueError
        return items
    except (ValueError, OSError) as exc:
        raise ValueError("Could not read saved logo presets; existing file was preserved.") from exc


def save_preset(base, name, asset_id, settings):
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
        raise ValueError("Enter a preset name up to 80 characters.")
    name = name.strip()
    asset_path(base, asset_id)
    settings = settings_for(settings)
    presets = list_presets(base)
    if any(item.get("name", "").casefold() == name.casefold() for item in presets):
        raise ValueError("A preset with this name already exists. Choose a new name.")
    presets.append({"name": name, "asset_id": asset_id, "settings": settings})
    path = presets_path(base)
    temp = path.with_name(f".{uuid.uuid4().hex}.tmp")
    try:
        temp.write_text(json.dumps(presets, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    return presets[-1]


def source_image(root, relative):
    source = Path(root).resolve()
    if not source.is_dir() or not relative or Path(relative).is_absolute():
        raise ValueError("Choose a source folder and a preview image inside it.")
    path = (source / relative).resolve()
    if not path.is_relative_to(source) or not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}:
        raise ValueError("The preview image must be inside the selected source folder.")
    return path


def composite(image, logo, settings):
    settings = settings_for(settings)
    rotation = settings["rotation"]
    if rotation:
        logo = logo.transpose({90: Image.Transpose.ROTATE_270, 180: Image.Transpose.ROTATE_180,
                               270: Image.Transpose.ROTATE_90}[rotation])
    width, height = image.size
    offset_x = round(width * settings["offset_x_pct"] / 100)
    offset_y = round(height * settings["offset_y_pct"] / 100)
    if settings["size_mode"] == "proportional":
        mark_width = max(1, round(width * settings["width_pct"] / 100))
        mark_height = max(1, round(mark_width * logo.height / logo.width))
    else:
        if settings["size_mode"] == "fit":
            available_width, available_height = width - 2 * offset_x, height - 2 * offset_y
            if available_width <= 0 or available_height <= 0:
                raise ValueError("Insets leave no room for the logo.")
            scale = min(available_width / logo.width, available_height / logo.height)
        else:
            scale = max(width / logo.width, height / logo.height)
        mark_width = max(1, round(logo.width * scale))
        mark_height = max(1, round(logo.height * scale))
    if mark_width * mark_height > 50_000_000:
        raise ValueError("The logo is too large for this image. Try Proportional or Fit.")
    vertical, horizontal = settings["position"].split("-")
    x = {"left": offset_x, "center": (width - mark_width) // 2 + offset_x,
         "right": width - mark_width - offset_x}[horizontal]
    y = {"top": offset_y, "middle": (height - mark_height) // 2 + offset_y,
         "bottom": height - mark_height - offset_y}[vertical]
    if settings["size_mode"] != "fill" and (x < 0 or y < 0 or x + mark_width > width or y + mark_height > height):
        raise ValueError("The logo does not fit inside this image. Reduce its size or offsets.")
    mark = logo.resize((mark_width, mark_height), Image.Resampling.LANCZOS)
    if settings["opacity_pct"] != 100:
        opacity = settings["opacity_pct"] / 100
        mark.putalpha(mark.getchannel("A").point(lambda value: round(value * opacity)))
    result = image.convert("RGBA")
    left, top = max(0, x), max(0, y)
    right, bottom = min(width, x + mark_width), min(height, y + mark_height)
    if left >= right or top >= bottom:
        raise ValueError("The logo is outside this image. Reduce the offsets.")
    visible = mark.crop((left - x, top - y, right - x, bottom - y))
    result.alpha_composite(visible, (left, top))
    return result


def render(path, logo, settings):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        info = {"icc_profile": source.info.get("icc_profile")}
        if source.getexif():
            info["exif"] = image.getexif().tobytes()
        result = composite(image, logo, settings)
    return result, {k: v for k, v in info.items() if v}


def save_new_image(image, info, output):
    """Publish without overwriting an existing file, even on simultaneous access."""
    temporary = output.with_name(f".{output.stem}.{uuid.uuid4().hex}.tmp{output.suffix}")
    try:
        save_options = dict(info)
        if output.suffix.lower() in {".jpg", ".jpeg"}:
            image = image.convert("RGB")
            save_options.update(quality=95, subsampling=0)
        elif output.suffix.lower() == ".webp":
            save_options.update(quality=95)
        image.save(temporary, **save_options)
        with Image.open(temporary) as check:
            check.verify()
        try:
            os.link(temporary, output)
        except FileExistsError:
            return False
        except OSError:
            try:
                with temporary.open("rb") as source:
                    with output.open("xb") as target:
                        try:
                            shutil.copyfileobj(source, target)
                        except Exception:
                            target.close()
                            output.unlink(missing_ok=True)
                            raise
            except FileExistsError:
                return False
        return True
    finally:
        temporary.unlink(missing_ok=True)


def run_logo(job, base, source, destination, asset_id, settings):
    source, _, destination = validate_paths(source, destination)
    logo = read_logo(asset_path(base, asset_id))
    settings = settings_for(settings)
    files = images_under(source)
    job.update(total=len(files), phase="Preparing folders", device={"name": "CPU", "provider": "cpu"})
    copy_folder_structure(job, source, destination)
    job.update(phase="Processing")
    for file in files:
        job.check_cancel()
        relative = file.relative_to(source)
        job.update(current_file=relative.as_posix())
        target = destination / relative
        try:
            if not target.parent.resolve().is_relative_to(destination):
                raise ValueError("Output folder contains a link outside the selected destination.")
            if target.exists():
                job.skip_file()
                job.log(f"Skipped existing output: {relative}")
                continue
            result, info = render(file, logo, settings)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not save_new_image(result, info, target):
                job.skip_file()
                job.log(f"Skipped existing output: {relative}")
                continue
            job.complete_file(True)
            job.log(f"Logo added: {relative}")
        except Exception as exc:
            job.complete_file(False)
            job.log(f"ERROR {relative}: {exc}")
    return {"total": len(files), "succeeded": job.data["succeeded"], "failed": job.data["failed"],
            "skipped": job.data["skipped"], "source_dir": str(source), "output_dir": str(destination)}
