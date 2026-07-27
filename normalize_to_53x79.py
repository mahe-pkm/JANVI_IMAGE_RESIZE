"""
Center-crop images to aspect ratio 53:79 and resize to 848x1264.
Saves results under ./normalized_53x79/<source_folder>/ and writes a CSV log.
Run:
C:/Users/rough/AppData/Local/Programs/Python/Python311/python.exe normalize_to_53x79.py
"""
from pathlib import Path
from PIL import Image
import csv

BASE = Path(r"c:\Users\rough\Desktop\Logo Processing\May-20261")
OUT_ROOT = BASE / 'normalized_53x79'
OUT_ROOT.mkdir(parents=True, exist_ok=True)
TARGET_W, TARGET_H = 848, 1264
TARGET_RATIO = TARGET_W / TARGET_H

processed = 0
errors = 0
log_rows = []

folders = [p for p in sorted(BASE.iterdir()) if p.is_dir() and (p.name.endswith('_selected_images') or p.name=='normalized_9x16')]
for folder in folders:
    out_folder = OUT_ROOT / folder.name
    out_folder.mkdir(parents=True, exist_ok=True)
    for f in sorted(folder.glob('*.png')):
        try:
            with Image.open(f) as im:
                im = im.convert('RGB')
                w,h = im.size
                cur_ratio = w / h
                if cur_ratio > TARGET_RATIO:
                    new_w = int(TARGET_RATIO * h)
                    left = (w - new_w)//2
                    im2 = im.crop((left, 0, left+new_w, h))
                else:
                    new_h = int(w / TARGET_RATIO)
                    top = (h - new_h)//2
                    im2 = im.crop((0, top, w, top+new_h))
                im_out = im2.resize((TARGET_W, TARGET_H), Image.LANCZOS)
                out_path = out_folder / f.name
                im_out.save(out_path, optimize=True)
                log_rows.append({'folder':folder.name,'filename':f.name,'orig_w':w,'orig_h':h,'out_w':TARGET_W,'out_h':TARGET_H,'out_path':str(out_path.relative_to(BASE)),'error':''})
                processed += 1
        except Exception as e:
            errors += 1
            log_rows.append({'folder':folder.name,'filename':f.name,'orig_w':'','orig_h':'','out_w':'','out_h':'','out_path':'','error':str(e)})

log_csv = OUT_ROOT / 'normalized_53x79_log.csv'
with log_csv.open('w', newline='', encoding='utf-8') as f:
    fields = ['folder','filename','orig_w','orig_h','out_w','out_h','out_path','error']
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for r in log_rows:
        writer.writerow(r)

print(f'Processed: {processed}, Errors: {errors}, Log: {log_csv}')
