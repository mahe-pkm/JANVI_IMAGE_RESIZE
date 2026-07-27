"""
Normalize images to 9:16 (default crop -> 1080x1920).
Run: C:/Users/rough/AppData/Local/Programs/Python/Python311/python.exe normalize_to_9x16.py
"""
from pathlib import Path
from PIL import Image
import csv

BASE = Path(r"c:\Users\rough\Desktop\Logo Processing\May-20261")
OUT_ROOT = BASE / "normalized_9x16"
TARGET_W, TARGET_H = 1080, 1920
METHOD = "crop"  # change to 'pad' to letterbox instead
PAD_COLOR = (255,255,255)

OUT_ROOT.mkdir(parents=True, exist_ok=True)
log_rows=[]
processed=0
errors=0

for folder in sorted(p for p in BASE.iterdir() if p.is_dir() and p.name!=OUT_ROOT.name):
    out_folder = OUT_ROOT / folder.name
    out_folder.mkdir(parents=True, exist_ok=True)
    for f in sorted(folder.glob('*.png')):
        try:
            with Image.open(f) as im:
                w,h = im.size
                target_ratio = TARGET_W / TARGET_H
                cur_ratio = w / h
                if METHOD=='crop':
                    if cur_ratio>target_ratio:
                        new_w=int(target_ratio*h)
                        left=(w-new_w)//2
                        im2=im.crop((left,0,left+new_w,h))
                    else:
                        new_h=int(w/target_ratio)
                        top=(h-new_h)//2
                        im2=im.crop((0,top,w,top+new_h))
                    im_out = im2.resize((TARGET_W,TARGET_H), Image.LANCZOS)
                    method='crop'
                else:
                    if cur_ratio>target_ratio:
                        new_w=TARGET_W
                        new_h=int(TARGET_W/cur_ratio)
                    else:
                        new_h=TARGET_H
                        new_w=int(TARGET_H*cur_ratio)
                    im2=im.resize((new_w,new_h), Image.LANCZOS)
                    canvas=Image.new('RGB',(TARGET_W,TARGET_H),PAD_COLOR)
                    canvas.paste(im2,((TARGET_W-new_w)//2,(TARGET_H-new_h)//2))
                    im_out=canvas
                    method='pad'
                out_path = out_folder / f.name
                im_out.save(out_path, optimize=True)
                log_rows.append({'folder':folder.name,'filename':f.name,'orig_w':w,'orig_h':h,'method':method,'out_w':TARGET_W,'out_h':TARGET_H,'out_path':str(out_path.relative_to(BASE)),'error':''})
                processed+=1
        except Exception as e:
            errors+=1
            log_rows.append({'folder':folder.name,'filename':f.name,'orig_w':'','orig_h':'','method':'','out_w':'','out_h':'','out_path':'','error':str(e)})

log_csv = OUT_ROOT / 'normalized_log.csv'
with log_csv.open('w',newline='',encoding='utf-8') as f:
    fields=['folder','filename','orig_w','orig_h','method','out_w','out_h','out_path','error']
    w=csv.DictWriter(f,fieldnames=fields)
    w.writeheader()
    for r in log_rows:
        w.writerow(r)

print(f'Processed: {processed}, Errors: {errors}. Log written to: {log_csv}')
