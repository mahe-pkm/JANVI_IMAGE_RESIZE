"""Release-time only. End users run the packaged ONNX model without PyTorch."""
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
(ROOT / ".build" / "ultralytics").mkdir(parents=True, exist_ok=True)
os.environ["YOLO_CONFIG_DIR"] = str(ROOT / ".build" / "ultralytics")

if __name__ == "__main__":
    from ultralytics import YOLO
    exported = YOLO(str(ROOT / "yolov8n.pt")).export(format="onnx", imgsz=640, opset=17,
                                                     simplify=False, dynamic=False, nms=False, device="cpu")
    output = ROOT / "models" / "yolov8n.onnx"
    output.parent.mkdir(exist_ok=True)
    shutil.move(str(exported), output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    (output.parent / "manifest.json").write_text(json.dumps({"file": output.name, "sha256": digest,
        "source_sha256": hashlib.sha256((ROOT / "yolov8n.pt").read_bytes()).hexdigest(),
        "input_size": 640, "opset": 17, "confidence": 0.5, "iou": 0.7}, indent=2), encoding="utf-8")
    print(f"Packaged {output}: {digest}")
