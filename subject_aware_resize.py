import os
from pathlib import Path
from PIL import Image
from ultralytics import YOLO

# ---------------- CONFIGURATION ----------------
BASE_DIR = Path(os.environ.get("BASE_DIR", Path(__file__).resolve().parent))
SOURCE_DIR = BASE_DIR / "Resizing"
DEST_DIR = BASE_DIR / "Re-sized"
TARGET_W, TARGET_H = 1200, 1800

# If True, the script will pad the image instead of cropping if the subject is too wide/tall to fit in the crop window.
STRICT_NO_SUBJECT_CROP = True 
PAD_COLOR = (255, 255, 255)
# -----------------------------------------------

def get_model():
    print("Loading Subject Detection Model (YOLOv8)...")
    model = YOLO('yolov8n.pt')
    print("Model loaded.")
    return model, None

def get_subject_bbox(model, device, img):
    results = model(img, verbose=False)
    
    people = []
    for r in results:
        boxes = r.boxes
        for box in boxes:
            if int(box.cls[0]) == 0 and float(box.conf[0]) > 0.5:
                people.append(box.xyxy[0].tolist())
    
    if not people:
        return None # No subject found
    
    # Find the largest bounding box (main subject)
    largest_box = None
    max_area = 0
    for box in people:
        xmin, ymin, xmax, ymax = box
        area = (xmax - xmin) * (ymax - ymin)
        if area > max_area:
            max_area = area
            largest_box = box
            
    return largest_box

def smart_crop_and_resize(img, bbox):
    w, h = img.size
    target_ratio = TARGET_W / TARGET_H
    cur_ratio = w / h
    
    # Subject center
    if bbox:
        xmin, ymin, xmax, ymax = bbox
        cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
        subject_w = xmax - xmin
        subject_h = ymax - ymin
    else:
        cx, cy = w / 2, h / 2
        subject_w, subject_h = 0, 0

    use_padding = False

    if cur_ratio > target_ratio:
        # Image is wider than target. We need to crop width.
        crop_w = int(h * target_ratio)
        crop_h = h
        
        if STRICT_NO_SUBJECT_CROP and bbox and subject_w > crop_w:
            use_padding = True
        else:
            left = cx - crop_w / 2
            # clamp
            left = max(0, min(w - crop_w, left))
            img_cropped = img.crop((left, 0, left + crop_w, h))
    else:
        # Image is taller than target. We crop height if the subject fits inside.
        crop_w = w
        crop_h = int(w / target_ratio)
        
        if STRICT_NO_SUBJECT_CROP and bbox and subject_h > crop_h:
            use_padding = True
        else:
            top = cy - crop_h / 2
            # clamp
            top = max(0, min(h - crop_h, top))
            img_cropped = img.crop((0, top, w, top + crop_h))

    if use_padding:
        from PIL import ImageFilter
        # Fallback to blurred background padding so we don't crop the subject
        
        # 1. Create the blurred background
        bg_ratio = w / h
        if bg_ratio > target_ratio:
            # Scale by height to ensure it covers the target height
            bg_h = TARGET_H
            bg_w = int(TARGET_H * bg_ratio)
        else:
            # Scale by width to ensure it covers the target width
            bg_w = TARGET_W
            bg_h = int(TARGET_W / bg_ratio)
            
        bg_img = img.resize((bg_w, bg_h), Image.LANCZOS)
        
        # Center crop the scaled image to exactly TARGET_W x TARGET_H
        bg_left = (bg_w - TARGET_W) // 2
        bg_top = (bg_h - TARGET_H) // 2
        bg_img = bg_img.crop((bg_left, bg_top, bg_left + TARGET_W, bg_top + TARGET_H))
        
        # Apply a minimal Gaussian blur
        bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=5))

        if cur_ratio > target_ratio:
            new_w = TARGET_W
            new_h = int(TARGET_W / cur_ratio)
            img_resized = img.resize((new_w, new_h), Image.LANCZOS)
            bg_img.paste(img_resized, (0, (TARGET_H - new_h) // 2))
            return bg_img, True
        else:
            new_h = TARGET_H
            new_w = int(TARGET_H * cur_ratio)
            img_resized = img.resize((new_w, new_h), Image.LANCZOS)
            bg_img.paste(img_resized, ((TARGET_W - new_w) // 2, 0))
            return bg_img, True
    else:
        # Standard resize after crop
        return img_cropped.resize((TARGET_W, TARGET_H), Image.LANCZOS), False

def main():
    import sys
    # Allow passing a subfolder name (e.g. 19-may-2026) via CLI arguments
    subfolder = sys.argv[1] if len(sys.argv) > 1 else ""
    search_dir = SOURCE_DIR / subfolder if subfolder else SOURCE_DIR
    
    if not search_dir.exists():
        print(f"Error: Directory {search_dir} does not exist.")
        return
        
    model, device = get_model()
    
    # Collect all images under search_dir
    image_paths = []
    for ext in ['*.png', '*.jpg', '*.jpeg']:
        image_paths.extend(list(search_dir.rglob(ext)))
        
    print(f"Found {len(image_paths)} images to process under {search_dir}.")
    
    padded_files = []
    
    for i, img_path in enumerate(image_paths):
        # Calculate destination path relative to SOURCE_DIR
        rel_path = img_path.relative_to(SOURCE_DIR)
        dest_path = DEST_DIR / rel_path
        
        # Create directories
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"[{i+1}/{len(image_paths)}] Processing {rel_path}...")
        try:
            with Image.open(img_path).convert("RGB") as img:
                bbox = get_subject_bbox(model, device, img)
                result_img, used_pad = smart_crop_and_resize(img, bbox)
                result_img.save(dest_path)
                if used_pad:
                    padded_files.append(rel_path)
        except Exception as e:
            print(f"Error processing {img_path.name}: {e}")
            
    list_path = DEST_DIR / "manual_patch_list.md"
    
    # Read existing padded files to merge them
    existing_items = set()
    if list_path.exists():
        with open(list_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("- `") and line.endswith("`"):
                    item = line[3:-1]
                    existing_items.add(item.replace('/', '\\'))
                    
    # Add new padded files
    for p in padded_files:
        existing_items.add(str(p).replace('/', '\\'))
        
    with open(list_path, "w", encoding="utf-8") as f:
        f.write("# Images Requiring Manual Patch (Padded)\n\n")
        for item in sorted(list(existing_items)):
            f.write(f"- `{item}`\n")
            
    print("Done!")

if __name__ == '__main__':
    main()
