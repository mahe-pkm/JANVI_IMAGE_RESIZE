"""Build the standalone browser-based Janvi Local Server ZIP for Windows x64."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    config = json.loads((ROOT / "local-server.json").read_text(encoding="utf-8"))
    version = config["version"]
    release_dir = ROOT / "dist" / f"v{version}"
    name = f"Janvi-Image-Studio-Local-Server-{version}-win-x64"
    package = release_dir / f"{name}.zip"
    if package.exists():
        raise FileExistsError("Preserving the existing package; bump local-server.json first.")

    build_root = ROOT / ".build" / "local-server-builds" / version / uuid.uuid4().hex[:8]
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_release.py"), "--name", name,
         "--output-dir", str(build_root), "--no-zip"],
        check=True,
    )
    payload = build_root / name
    for source, destination in {
        "LOCAL_SERVER_README.md": "LOCAL_SERVER_README.md",
        "START_JANVI_LOCAL_SERVER.cmd": "START_JANVI_LOCAL_SERVER.cmd",
        "STOP_JANVI_LOCAL_SERVER.cmd": "STOP_JANVI_LOCAL_SERVER.cmd",
        "JANVI_LOCAL_SERVER_CONSOLE.ps1": "JANVI_LOCAL_SERVER_CONSOLE.ps1",
        "local-server.json": "local-server.json",
    }.items():
        shutil.copy2(ROOT / source, payload / destination)

    release_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in payload.rglob("*"):
            if file.is_file():
                archive.write(file, Path(name) / file.relative_to(payload))
    package.with_suffix(".zip.sha256").write_text(
        f"{digest(package)}  {package.name}\n", encoding="ascii"
    )
    print(f"Local Server release: {package}")


if __name__ == "__main__":
    main()
