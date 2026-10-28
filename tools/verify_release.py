"""Exercise a running release through HTTP, with fixtures inside this checkout."""
import hashlib
import json
from pathlib import Path
import time
import urllib.request
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--output", default="portable-validation.json")
    args = parser.parse_args()
    fixtures = ROOT / ".build" / "fixtures"
    originals = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fixtures.iterdir() if p.is_file()}
    def request(path, data=None):
        payload = json.dumps(data).encode() if data is not None else None
        query = urllib.request.Request(args.url + path, data=payload,
                                       headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(query, timeout=15) as response:
            return json.load(response)
    devices = request("/api/devices")["devices"]
    report = []
    for device in devices:
        if not device["available"]:
            continue
        output = ROOT / ".build" / ("portable-output-" + device["kind"])
        request("/api/resize", {"root_dir": str(fixtures), "dest_dir": str(output), "device_id": device["id"]})
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            status = request("/api/status")
            if not status["active"]:
                break
            time.sleep(.2)
        else:
            raise TimeoutError(device["name"])
        assert status["status"] == "completed", status
        assert status["succeeded"] == len(originals), status
        outputs = []
        for file in fixtures.iterdir():
            if file.name not in originals:
                continue
            with Image.open(output / file.name) as image:
                assert image.size == (1200, 1800), image.size
                image.verify()
            assert hashlib.sha256(file.read_bytes()).hexdigest() == originals[file.name]
            outputs.append(file.name)
        report.append({"device": device["name"], "kind": device["kind"], "status": status["status"],
                       "succeeded": status["succeeded"], "failed": status["failed"], "outputs": outputs,
                       "source_checksums_unchanged": True, "actual_device": status["device"]})
        print(device["name"], status["status"], len(outputs), "verified outputs", flush=True)
    metrics = request("/api/telemetry")
    for _ in range(20):
        if metrics.get("ram_total_bytes", 0) > 0:
            break
        time.sleep(.2)
        metrics = request("/api/telemetry")
    assert metrics.get("ram_total_bytes", 0) > 0
    (ROOT / ".build" / args.output).write_text(json.dumps({"jobs": report, "telemetry": metrics}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
