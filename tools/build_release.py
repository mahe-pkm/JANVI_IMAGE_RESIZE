"""Assemble a clean offline distribution. Never copy user data or virtualenvs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="Janvi-Image-Resize-0.2.0-portable-win-x64")
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist')
    parser.add_argument('--no-zip', action='store_true')
    args = parser.parse_args()
    if Path(args.name).name != args.name or args.name in (".", ".."):
        raise ValueError("Release name must be a single folder name")
    destination = args.output_dir.resolve() / args.name
    if destination.exists():
        raise FileExistsError(f"Use a new release name; preserving {destination}")
    wheels = ROOT / ".build" / "wheels"
    release_manifest = json.loads((ROOT / "package-manifest.json").read_text(encoding="utf-8-sig"))
    wheel_files = [wheels / entry["file"] for entry in release_manifest["wheels"]]
    if len(wheel_files) != 18:
        raise RuntimeError("Prepare all 17 pinned dependency wheels plus pip before packaging")
    for entry, wheel in zip(release_manifest["wheels"], wheel_files):
        if digest(wheel) != entry["sha256"]:
            raise ValueError(f"Dependency checksum mismatch: {wheel.name}")
    destination.mkdir(parents=True)
    for name in ["app.py", "jobs.py", "processing.py", "photoshop_repair.py", "inference.py", "hardware.py", "telemetry.py",
                 "subject_aware_resize.py", "move_to_shopify.py", "logo_processing.py", "launch.py", "select_folder.ps1", "Start.cmd", "Start.ps1",
                 "Stop.ps1", "requirements.txt", "runtime-manifest.json", "README.md", "CHANGELOG.md", "VERIFICATION.md", "THIRD_PARTY_NOTICES.md"]:
        shutil.copy2(ROOT / name, destination / name)
    for name in ["static", "templates", "models", "assets", "photoshop", "docs"]:
        shutil.copytree(ROOT / name, destination / name)
    (destination / "desktop").mkdir()
    for name in ["README.md", "VERIFICATION.md"]:
        shutil.copy2(ROOT / "desktop" / name, destination / "desktop" / name)
    (destination / "wheels").mkdir()
    for wheel in wheel_files:
        shutil.copy2(wheel, destination / "wheels" / wheel.name)
    shutil.copytree(ROOT / ".build" / "redist", destination / "redist")
    archive = ROOT / ".build" / "runtime-python.zip"
    manifest = json.loads((ROOT / "runtime-manifest.json").read_text(encoding="utf-8-sig"))
    if digest(archive) != manifest["sha256"]:
        raise ValueError("Python archive checksum mismatch")
    shutil.copy2(archive, destination / "runtime-python.zip")
    launcher = ROOT / ".build" / "cargo" / "release" / "janvi-launcher.exe"
    if launcher.exists():
        shutil.copy2(launcher, destination / "JanviLauncher.exe")
    (destination / "package-manifest.json").write_text(json.dumps(release_manifest, indent=2), encoding="utf-8")
    if args.no_zip:
        print(f'Created backend payload {destination}')
        return
    package = args.output_dir.resolve() / f"{args.name}.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as output:
        for path in destination.rglob("*"):
            if path.is_file():
                output.write(path, Path(args.name) / path.relative_to(destination))
    package.with_suffix(".zip.sha256").write_text(digest(package) + "  " + package.name + "\n", encoding="ascii")
    print(f"Created {package} ({package.stat().st_size / 1048576:.1f} MB)")


if __name__ == "__main__":
    main()
