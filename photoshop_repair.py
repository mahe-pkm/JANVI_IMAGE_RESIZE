"""Record exact padding bounds and generate a relocatable Photoshop queue."""
import hashlib
import json
import os
import zlib
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / 'photoshop' / 'repair-template.jsx'
MANIFEST = 'padding_manifest.json'
SCRIPT = 'Repair_Padding.jsx'


def checksum(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def file_checksum(path):
    crc, size = 0, 0
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            crc = zlib.crc32(chunk, crc)
            size += len(chunk)
    return f'{crc & 0xffffffff:08x}:{size}'


def atomic_text(path, text):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(text, encoding='utf-8')
    os.replace(temporary, path)


def update_padding_queue(destination, records, job_id, existing_paths):
    destination = Path(destination)
    path = destination / MANIFEST
    previous = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    entries = {entry['file']: entry for entry in previous.get('entries', [])}
    for record in records:
        if record['status'] != 'ok':
            continue
        relative = record['file']
        entries.pop(relative, None)
        if record['padded'] and record.get('geometry'):
            entries[relative] = dict(file=relative, sha256=checksum(destination / relative),
                                     file_checksum=file_checksum(destination / relative),
                                     geometry=record['geometry'])
    entries = {name: value for name, value in entries.items() if name in existing_paths}
    ordered = [entries[name] for name in sorted(entries)]
    fingerprint = hashlib.sha256(json.dumps(ordered, sort_keys=True).encode()).hexdigest()[:20]
    unknown = sorted(set(existing_paths) - set(entries))
    manifest = dict(schema_version=1, fingerprint=fingerprint, job_id=job_id,
                    original_root=str(destination.resolve()),
                    entries=ordered, missing_geometry=unknown,
                    report=f'photoshop-report-{fingerprint}.json')
    atomic_text(path, json.dumps(manifest, indent=2))
    # JSON is embedded as a JS literal, never interpolated into executable strings.
    payload = json.dumps(manifest, ensure_ascii=True).replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    atomic_text(destination / SCRIPT, TEMPLATE.read_text(encoding='utf-8').replace('/*__JANVI_QUEUE__*/null', payload))
    for launcher in ('Start_Photoshop_Repair.cmd', 'Start_Photoshop_Repair.ps1'):
        atomic_text(destination / launcher, (TEMPLATE.parent / launcher).read_text(encoding='utf-8'))
    lines = ['# Images Requiring Manual Patch (Padded)', '',
             'Run `Repair_Padding.jsx` from Photoshop: File > Scripts > Browse.',
             'Only files with recorded geometry and matching checksums are processed.', '']
    for name in sorted(existing_paths):
        lines.append(f'- `{name}`')
        if name in entries:
            geometry = entries[name]['geometry']
            padding = geometry['padding']
            content = geometry['content']
            lines.append(f"  Canvas: {geometry['canvas_width']} x {geometry['canvas_height']} px")
            lines.append('  Padding: ' + ', '.join(f'{side} {padding[side]} px' for side in ('left', 'right', 'top', 'bottom')))
            lines.append('  Content: ' + ', '.join(f'{key}={content[key]}' for key in ('x', 'y', 'width', 'height')))
        else:
            lines.append('  Geometry unavailable: resize again from the original before automated repair.')
    atomic_text(destination / 'manual_patch_list.md', '\n'.join(lines) + '\n')
    return manifest


def repair_status(destination):
    destination = Path(destination).resolve()
    path = destination / MANIFEST
    if not path.exists():
        return dict(available=False, message='Resize with padding metadata to create a Photoshop script.')
    manifest = json.loads(path.read_text(encoding='utf-8'))
    report_path = destination / manifest['report']
    report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {}
    payload = json.dumps(manifest, ensure_ascii=True).replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    expected = TEMPLATE.read_text(encoding='utf-8').replace('/*__JANVI_QUEUE__*/null', payload)
    script_path = destination / SCRIPT
    valid_script = script_path.is_file() and script_path.read_text(encoding='utf-8') == expected
    return dict(available=True, valid_script=valid_script, script=str(script_path), total=len(manifest['entries']),
                missing_geometry=len(manifest.get('missing_geometry', [])),
                report=report, message='Run the script in Photoshop, then refresh this status and review the results.')
