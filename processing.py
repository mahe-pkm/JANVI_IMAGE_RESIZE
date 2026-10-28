"""Shared, source-preserving file operations used by every inference backend."""
import json
import hashlib
import os
from pathlib import Path
import shutil
import uuid
from PIL import Image, ImageOps
from subject_aware_resize import smart_crop_and_resize, crop_decision, TARGET_W, TARGET_H
from photoshop_repair import update_padding_queue

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def images_under(root, recursive=True, extensions=EXTENSIONS):
    iterator = root.rglob("*") if recursive else root.iterdir()
    return sorted({p.resolve() for p in iterator if p.is_file() and p.suffix.lower() in extensions}, key=str)


def validate_paths(source, destination=None, folder=""):
    source = Path(source).resolve()
    selected = (source / folder).resolve()
    if not source.is_dir() or not selected.is_dir() or not selected.is_relative_to(source):
        raise ValueError("Choose an existing source directory and a collection inside it.")
    destination = Path(destination).resolve() if destination else source.with_name(source.name + "_resized")
    if destination == source or destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("Source and output must be separate folders; neither may contain the other.")
    if any((root / '.janvi-photoshop-running').exists() for root in (source, destination)):
        raise ValueError('A Photoshop padding repair may be active in this folder. Finish or cancel it before starting another operation.')
    return source, selected, destination


def atomic_image(image, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.stem}.{uuid.uuid4().hex}.tmp{destination.suffix}")
    try:
        image.save(temporary)
        with Image.open(temporary) as check:
            check.verify()
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def run_images(job, kind, source, destination, folder, device_id, target_width=TARGET_W, target_height=TARGET_H):
    from inference import Detector
    source, selected, destination = validate_paths(source, destination, folder)
    files = images_under(selected)
    job.update(total=len(files))
    job.log(f"Found {len(files)} images. Source: {source}")
    if not files:
        return {"total": 0, "message": "No supported images found."}
    job.check_cancel()
    job.update(phase="Loading model")
    detector = Detector(device_id)
    job.update(device=detector.device, phase="Processing")
    job.log(f"Detection: {detector.device['name']} ({detector.device['provider']})")
    padded = []
    records = []
    try:
        for file in files:
            job.check_cancel()
            relative = file.relative_to(source)
            job.update(current_file=relative.as_posix())
            try:
                geometry = None
                with Image.open(file) as original:
                    image = ImageOps.exif_transpose(original).convert("RGB")
                bbox = (None if image.width * target_height == image.height * target_width
                        else detector.detect(image))
                decision = crop_decision(image.size, bbox, target_width, target_height)
                if kind == "audit":
                    pad = decision['padded']
                else:
                    result, pad, geometry = smart_crop_and_resize(image, bbox, include_geometry=True, target_width=target_width, target_height=target_height)
                    atomic_image(result, destination / relative)
                if pad:
                    padded.append(relative.as_posix())
                records.append({"file": relative.as_posix(), "status": "ok", "padded": pad, "geometry": geometry,
                                "crop_reason": decision['reason'], "subject_box": bbox})
                job.complete_file(True)
                reason = {'correct_ratio': 'already 2:3', 'no_subject_detected': 'no subject detected; review',
                          'invalid_subject_box': 'invalid detection; review', 'subject_margin': 'subject needs extra space',
                          'subject_crop': 'subject with safety margin'}[decision['reason']]
                job.log(f"{'Padded' if pad else 'Crop ready' if kind == 'audit' else 'Resized'} ({reason}): {relative}")
            except Exception as exc:
                records.append({"file": relative.as_posix(), "status": "failed", "error": str(exc)})
                job.complete_file(False)
                job.log(f"ERROR {relative}: {exc}")
    finally:
        detector.close()
        if kind == "resize":
            destination.mkdir(parents=True, exist_ok=True)
            # Preserve the gallery index when a job was cancelled partway through.
            patch = destination / "manual_patch_list.md"
            existing = set()
            if patch.exists():
                existing = {line[3:-1].replace("\\", "/") for line in patch.read_text(encoding="utf-8").splitlines()
                            if line.startswith("- `") and line.endswith("`")}
            successful = {r["file"] for r in records if r["status"] == "ok"}
            existing.difference_update(successful)
            existing.update(padded)
            update_padding_queue(destination, records, job.data['job_id'], existing)
            job.log(f'Photoshop padding script: {destination / "Repair_Padding.jsx"}')
            (destination / f"job-{job.data['job_id']}.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    return {"total": len(files), "padded": len(padded), "succeeded": job.data["succeeded"], "failed": job.data["failed"]}


def copy_folder_structure(job, source, destination):
    # Preserve the source tree, including empty folders. Never follow a directory
    # link outside the chosen source or write through an output link outside it.
    def walk_error(error):
        raise error

    for root, dirs, _ in os.walk(source, followlinks=False, onerror=walk_error):
        job.check_cancel()
        current = Path(root)
        dirs[:] = [name for name in dirs
                   if not (current / name).is_symlink()
                   and (current / name).resolve().is_relative_to(source)]
        target = destination / current.relative_to(source)
        if not target.resolve().is_relative_to(destination):
            raise ValueError("Output folder contains a link outside the selected destination.")
        target.mkdir(parents=True, exist_ok=True)


def file_digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').digest()


def export_plan(source, destination, mode):
    if mode not in {'lightroom', 'native'}:
        raise ValueError('Choose Lightroom or native app export.')
    source, _, destination = validate_paths(source, destination)
    candidates = []
    def fail(error):
        raise error
    for root, dirs, names in os.walk(source, followlinks=False, onerror=fail):
        directory = Path(root)
        dirs[:] = [name for name in dirs if not (directory / name).is_symlink()]
        for name in names:
            file = directory / name
            if file.is_symlink() or not file.is_file() or file.suffix.lower() not in EXTENSIONS | {'.gif'}:
                continue
            if mode == 'lightroom' and directory.name.casefold() != 'untitled export':
                continue
            candidates.append(file)
    candidates.sort(key=lambda p: str(p.relative_to(source)))
    from move_to_shopify import get_product_name_for_folder, clean_product_name
    counts, entries, reserved = {}, [], set()
    for file in candidates:
        folder = file.parent
        if mode == 'lightroom':
            product = folder.parent
            relative_dir = product.relative_to(source) if product.is_relative_to(source) else Path('.')
            name = clean_product_name(product.name) or 'Product'
        else:
            product_folder = folder.parent if folder.name.casefold() == 'untitled export' else folder
            relative_dir = product_folder.relative_to(source) if product_folder.is_relative_to(source) else Path('.')
            name = get_product_name_for_folder(folder, source)
        key = (str(relative_dir).casefold(), name.casefold(), file.suffix.casefold())
        counts[key] = counts.get(key, 0) + 1
        relative_output = relative_dir / f'{name}_{counts[key]}{file.suffix.lower()}'
        identity = str(relative_output).casefold()
        if identity in reserved:
            raise ValueError(f'Multiple images map to the same output: {relative_output}')
        reserved.add(identity)
        output = destination / relative_output
        if not output.parent.resolve().is_relative_to(destination):
            raise ValueError('Output contains a folder link outside the destination.')
        status = 'copy'
        if output.exists() or output.is_symlink():
            if output.is_symlink() or not output.is_file():
                status = 'conflict'
            else:
                status = 'already_present' if file.stat().st_size == output.stat().st_size and file_digest(file) == file_digest(output) else 'conflict'
        entries.append({'source': file.relative_to(source).as_posix(), 'output': relative_output.as_posix(), 'status': status})
    return source, destination, entries


def export_signature(source, destination, mode, entries):
    stamps = []
    for entry in entries:
        info = (source / entry['source']).stat()
        stamps.append((entry['source'], entry['output'], entry['status'], info.st_size, info.st_mtime_ns))
    content = json.dumps([str(source), str(destination), mode, stamps], ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def run_export(job, source, destination, mode='native', reviewed_signature=None):
    source, destination, entries = export_plan(source, destination, mode)
    if reviewed_signature is not None and reviewed_signature != export_signature(source, destination, mode, entries):
        raise ValueError('Files or destinations changed after preview. Preview the export again.')
    job.update(total=len(entries), phase='Processing', device={'name': 'File copy (CPU)', 'provider': 'filesystem'})
    if not entries:
        raise ValueError('No eligible images found for the selected export mode.')
    for entry in entries:
        job.check_cancel()
        relative, output_relative = Path(entry['source']), Path(entry['output'])
        file, output = source / relative, destination / output_relative
        job.update(current_file=relative.as_posix())
        temporary = None
        try:
            if file.is_symlink() or not file.resolve().is_relative_to(source) or not file.is_file():
                raise ValueError('Source image is no longer available inside the selected folder.')
            if not output.parent.resolve().is_relative_to(destination):
                raise ValueError('Output folder contains a link outside the destination.')
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists() or output.is_symlink():
                if not output.is_symlink() and output.is_file() and file.stat().st_size == output.stat().st_size and file_digest(file) == file_digest(output):
                    job.skip_file(); job.log(f'Already present: {output_relative}'); continue
                raise FileExistsError('Output already exists with different contents; it was not overwritten.')
            temporary = output.with_name(f'.{output.name}.{uuid.uuid4().hex}.tmp')
            shutil.copy2(file, temporary)
            if temporary.stat().st_size != file.stat().st_size or file_digest(file) != file_digest(temporary):
                raise OSError('Output checksum verification failed')
            try:
                os.link(temporary, output)
            except FileExistsError:
                raise FileExistsError('Output appeared during export; it was not overwritten.') from None
            except OSError:
                try:
                    with output.open('xb') as target, temporary.open('rb') as copied:
                        try: shutil.copyfileobj(copied, target)
                        except Exception:
                            target.close(); output.unlink(missing_ok=True); raise
                except FileExistsError:
                    raise FileExistsError('Output appeared during export; it was not overwritten.') from None
            job.complete_file(True)
            job.log(f'Copied: {relative} -> {output_relative}')
        except Exception as exc:
            job.complete_file(False); job.log(f'ERROR {relative}: {exc}')
        finally:
            if temporary: temporary.unlink(missing_ok=True)
    return {'copied_files': job.data['succeeded'], 'skipped': job.data['skipped'], 'failed': job.data['failed'], 'source_files_preserved': True}
