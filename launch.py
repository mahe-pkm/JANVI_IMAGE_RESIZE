"""Portable entry point: verify assets, choose a free port, serve on loopback."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import threading
import webbrowser


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    os.chdir(root)
    manifest = json.loads((root / "models" / "manifest.json").read_text(encoding="utf-8"))
    model = root / "models" / manifest["file"]
    if hashlib.sha256(model.read_bytes()).hexdigest() != manifest["sha256"]:
        raise RuntimeError("Model checksum verification failed. Repair the application package.")
    from waitress import create_server
    from app import app, BASE_DIR
    server = create_server(app, host="127.0.0.1", port=args.port, threads=6)
    url = f"http://127.0.0.1:{server.effective_port}"
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "server.json").write_text(json.dumps({"pid": os.getpid(), "url": url}), encoding="utf-8")
    print(f"Janvi Image Resize: {url}", flush=True)
    if not args.no_browser:
        threading.Timer(.5, lambda: webbrowser.open(url)).start()
    try:
        server.run()
    finally:
        server.close()
        (BASE_DIR / "server.json").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
