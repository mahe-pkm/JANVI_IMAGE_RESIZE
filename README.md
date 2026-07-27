# JANVI_IMAGE_RESIZE: Subject-Aware Logo Processing Dashboard

A Flask-based web application and automated image processing tool that performs subject-aware cropping, padding, aspect ratio normalization, and logo detection using PyTorch and YOLOv8.

---

## ⚡ Installation

### Option 1: CPU-Only Installation (Recommended for PCs without GPU)
If your computer **does not have a dedicated NVIDIA GPU**, you still need `torch` and `torchvision`, but you should install the **lightweight CPU-only build** (~150 MB instead of ~2.5 GB):

```bash
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

Or manually:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install Flask Pillow ultralytics
```

---

### Option 2: Standard / GPU Installation
If your computer has an NVIDIA GPU with CUDA:

```bash
pip install -r requirements.txt
```

---

## 🚀 How to Run Locally

### On Windows (PowerShell):
```powershell
.\run_local.ps1
```

### Or using Python directly:
```bash
python app.py
```

Then open your browser and go to: **`http://127.0.0.1:5000`**

---

## 🛠 Features
- **Subject-Aware Smart Resizing**: Automatically detects people/subjects using YOLOv8 (`yolov8n.pt`) and centers the crop window to prevent clipping subjects.
- **Strict No-Subject-Crop & Smart Padding**: Automatically pads images with white/custom background when subjects are too wide or tall for exact target ratios.
- **Web Dashboard**: Interactive status tracking, image audit reports, and batch processing.
- **Aspect Ratio Normalization**: Normalizes images to standard ratios (e.g., `53:79` and `9:16`).
