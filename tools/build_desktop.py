"""Build clean Electron ZIP and MSI; preserve previous release versions."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import sys
import zipfile
import os
import uuid
import json

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / 'desktop/package.json').read_text(encoding='utf-8'))['version']

def main():
    release_dir = ROOT / 'dist' / f'v{VERSION}'
    name = f'Janvi-Image-Studio-{VERSION}-win-x64'
    zip_path, msi_path = release_dir / f'{name}.zip', release_dir / f'{name}.msi'
    if zip_path.exists() or msi_path.exists(): raise FileExistsError('Preserving previous desktop release; bump the version before building.')
    build = ROOT / '.build' / 'desktop-builds' / VERSION / uuid.uuid4().hex[:8]
    staging = build / 'payload'
    subprocess.run([sys.executable, str(ROOT / 'tools/build_release.py'), '--name', 'backend', '--output-dir', str(staging), '--no-zip'], check=True)
    subprocess.run(['node', 'package-release.js'], cwd=ROOT / 'desktop', check=True, env={**os.environ, 'JANVI_BUILD_ROOT': str(build)})
    desktop = build / 'package' / 'Janvi Image Studio-win32-x64'
    shutil.copytree(staging / 'backend', desktop / 'resources' / 'backend')
    shutil.copy2(ROOT / 'desktop/janvi.cmd', desktop / 'janvi.cmd')
    shutil.copy2(ROOT / 'desktop/README.md', desktop / 'README-DESKTOP.md')
    release_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in desktop.rglob('*'):
            if file.is_file(): archive.write(file, Path(name) / file.relative_to(desktop))
    checksum = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    zip_path.with_suffix('.zip.sha256').write_text(f'{checksum}  {zip_path.name}\n', encoding='ascii')
    subprocess.run([sys.executable, str(ROOT / 'tools/build_msi.py'), '--desktop', '--version', VERSION, '--release', str(desktop), '--output', str(msi_path)], check=True)
    print(f'Desktop release: {release_dir}')

if __name__ == '__main__': main()
