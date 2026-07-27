"""
GPU-accelerated image normalization to target aspect ratio 53:79 and size 848x1264.

This script loads source images from all <name>_selected_images folders plus normalized_9x16,
center-crops each image to the target ratio, resizes on GPU using Kornia, and saves to
normalized_53x79/<source_folder>/. A CSV log is written to normalized_53x79/normalized_53x79_log.csv.

Run:
C:/Users/rough/AppData/Local/Programs/Python/Python311/python.exe gpu_normalize_to_53x79.py
"""

from pathlib import Path
from PIL import Image
import csv
import torch
import torchvision.transforms.functional as TF
import torch.nn.functional as F
from tqdm import tqdm

TARGET_W, TARGET_H = 848, 1264
TARGET_RATIO = TARGET_W / TARGET_H

BASE = Path(r"c:\Users\rough\Desktop\Logo Processing\May-20261")
SRC_FOLDERS = [p for p in sorted(BASE.iterdir()) if p.is_dir() and (p.name.endswith('_selected_images') or p.name == 'normalized_9x16')]
OUT_ROOT = BASE / 'normalized_53x79'
OUT_ROOT.mkdir(parents=True, exist_ok=True)
LOG_CSV = OUT_ROOT / 'normalized_53x79_log.csv'
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

print(f'Running on device: {DEVICE}')
print('Source folders:', [p.name for p in SRC_FOLDERS])


def load_image_tensor(path: Path) -> torch.Tensor:
    with Image.open(path) as img:
        img = img.convert('RGB')
        tensor = TF.to_tensor(img)
    return tensor


def center_crop_to_ratio(img: torch.Tensor, target_ratio: float) -> torch.Tensor:
    _, h, w = img.shape
    cur_ratio = float(w) / float(h)
    if cur_ratio > target_ratio:
        new_w = int(round(target_ratio * h))
        left = (w - new_w) // 2
        return img[:, :, left:left + new_w]
    else:
        new_h = int(round(w / target_ratio))
        top = (h - new_h) // 2
        return img[:, top:top + new_h, :]


def save_tensor_as_image(tensor: torch.Tensor, path: Path) -> None:
    tensor = tensor.clamp(0.0, 1.0).cpu()
    img = TF.to_pil_image(tensor)
    img.save(path, optimize=True)


if __name__ == '__main__':
    file_list = []
    for folder in SRC_FOLDERS:
        file_list.extend(sorted(folder.glob('*.png')))

    log_rows = []
    processed = 0
    errors = 0

    for src_path in tqdm(file_list, desc='Images'):
        rel_folder = src_path.parent.name
        out_folder = OUT_ROOT / rel_folder
        out_folder.mkdir(parents=True, exist_ok=True)
        out_path = out_folder / src_path.name
        try:
            img = load_image_tensor(src_path)
            cropped = center_crop_to_ratio(img, TARGET_RATIO)
            batch = cropped.unsqueeze(0).to(DEVICE)
            resized = F.interpolate(batch, size=(TARGET_H, TARGET_W), mode='bicubic', align_corners=False)
            result = resized[0]
            save_tensor_as_image(result, out_path)
            log_rows.append({
                'folder': rel_folder,
                'filename': src_path.name,
                'src_w': img.shape[2],
                'src_h': img.shape[1],
                'cropped_w': cropped.shape[2],
                'cropped_h': cropped.shape[1],
                'out_w': TARGET_W,
                'out_h': TARGET_H,
                'out_path': str(out_path.relative_to(BASE)),
                'error': ''
            })
            processed += 1
        except Exception as exc:
            errors += 1
            log_rows.append({
                'folder': rel_folder,
                'filename': src_path.name,
                'src_w': '',
                'src_h': '',
                'cropped_w': '',
                'cropped_h': '',
                'out_w': '',
                'out_h': '',
                'out_path': '',
                'error': str(exc)
            })

    with LOG_CSV.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['folder', 'filename', 'src_w', 'src_h', 'cropped_w', 'cropped_h', 'out_w', 'out_h', 'out_path', 'error'])
        writer.writeheader()
        writer.writerows(log_rows)

    print(f'Processed: {processed}, Errors: {errors}, Log saved to {LOG_CSV}')
