"""Small ONNX YOLOv8 detector. No PyTorch is needed on end-user machines."""
from pathlib import Path
import numpy as np
from PIL import Image
import onnxruntime as ort
from hardware import inventory

MODEL = Path(__file__).resolve().parent / "models" / "yolov8n.onnx"


def nms(boxes, scores, threshold=0.7):
    order = np.argsort(scores)[::-1]
    keep = []
    while len(order):
        i = order[0]
        keep.append(i)
        other = order[1:]
        if not len(other):
            break
        lo = np.maximum(boxes[i, :2], boxes[other, :2])
        hi = np.minimum(boxes[i, 2:], boxes[other, 2:])
        overlap = np.prod(np.maximum(hi - lo, 0), axis=1)
        areas = np.prod(np.maximum(boxes[:, 2:] - boxes[:, :2], 0), axis=1)
        iou = overlap / np.maximum(areas[i] + areas[other] - overlap, 1e-9)
        order = other[iou <= threshold]
    return keep


class Detector:
    def __init__(self, device_id="cpu", profile=False):
        options = inventory()
        self.device = next((d for d in options if d["id"] == device_id), None)
        if not self.device or not self.device["available"]:
            raise ValueError("Selected device is unavailable. Choose CPU or repair the GPU runtime/driver.")
        settings = ort.SessionOptions()
        if profile:
            directory = MODEL.parent.parent / ".build" / "profiles"
            directory.mkdir(parents=True, exist_ok=True)
            settings.enable_profiling = True
            settings.profile_file_prefix = str(directory / "inference")
        settings.intra_op_num_threads = max(1, min(8, (__import__('os').cpu_count() or 2) - 1))
        if device_id == "cpu":
            providers = ["CPUExecutionProvider"]
        else:
            settings.enable_mem_pattern = False
            settings.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            providers = [("DmlExecutionProvider", {"device_id": self.device["index"]}), "CPUExecutionProvider"]
        self.session = ort.InferenceSession(str(MODEL), sess_options=settings, providers=providers)
        self.session.disable_fallback()
        if device_id != "cpu" and "DmlExecutionProvider" not in self.session.get_providers():
            raise RuntimeError("GPU session initialization fell back to CPU. Choose CPU explicitly.")
        self.input = self.session.get_inputs()[0].name
        self.size = int(self.session.get_inputs()[0].shape[2])
        # Validate that the selected execution path can actually run this model.
        self.session.run(None, {self.input: np.zeros((1, 3, self.size, self.size), dtype=np.float32)})
        self.device = dict(self.device, validated=True)

    def detect(self, image):
        width, height = image.size
        scale = min(self.size / width, self.size / height)
        resized = (round(width * scale), round(height * scale))
        pad_x, pad_y = (self.size - resized[0]) / 2, (self.size - resized[1]) / 2
        left, top = round(pad_x - .1), round(pad_y - .1)
        canvas = Image.new("RGB", (self.size, self.size), (114, 114, 114))
        canvas.paste(image.resize(resized, Image.Resampling.BILINEAR), (left, top))
        array = np.asarray(canvas, dtype=np.float32).transpose(2, 0, 1)[None] / 255.0
        predictions = self.session.run(None, {self.input: np.ascontiguousarray(array)})[0][0].T
        # Match the original policy: winning class is person, confidence > 0.5.
        classes = predictions[:, 4:].argmax(axis=1)
        scores = predictions[:, 4:].max(axis=1)
        selected = (classes == 0) & (scores > .5)
        rows, scores = predictions[selected], scores[selected]
        if not len(rows):
            return None
        boxes = np.column_stack((rows[:, :2] - rows[:, 2:4] / 2, rows[:, :2] + rows[:, 2:4] / 2))
        boxes = boxes[nms(boxes, scores)]
        boxes[:, [0, 2]] = np.clip((boxes[:, [0, 2]] - left) / scale, 0, width)
        boxes[:, [1, 3]] = np.clip((boxes[:, [1, 3]] - top) / scale, 0, height)
        areas = np.prod(boxes[:, 2:] - boxes[:, :2], axis=1)
        return boxes[areas.argmax()].tolist()

    def close(self):
        self.session = None
