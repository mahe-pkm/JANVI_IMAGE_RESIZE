import os
from pathlib import Path
from PIL import Image

# ---------------- CONFIGURATION ----------------
BASE_DIR = Path(os.environ.get("BASE_DIR", Path(__file__).resolve().parent))
SOURCE_DIR = BASE_DIR / "Resizing"
DEST_DIR = BASE_DIR / "Re-sized"
TARGET_W, TARGET_H = 1200, 1800

# If True, the script will pad the image instead of cropping if the subject is too wide/tall to fit in the crop window.
STRICT_NO_SUBJECT_CROP = True 
PAD_COLOR = (255, 255, 255)
SUBJECT_MARGIN = 0.05  # Fraction of source width/height, on each side.
# -----------------------------------------------

def get_model():
    print("Loading Subject Detection Model (YOLOv8)...")
    from ultralytics import YOLO
    model = YOLO(str(Path(__file__).resolve().parent / "yolov8n.pt"))
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

def padding_geometry(content_x, content_y, content_w, content_h, target_width=TARGET_W, target_height=TARGET_H):
    """Exact output-pixel rectangles, including asymmetric rounding at edges."""
    left, top = content_x, content_y
    right, bottom = target_width - left - content_w, target_height - top - content_h
    rectangles = []
    for side, x, y, width, height in [('left', 0, 0, left, target_height),
                                     ('right', target_width-right, 0, right, target_height),
                                     ('top', left, 0, content_w, top),
                                     ('bottom', left, target_height-bottom, content_w, bottom)]:
        if width > 0 and height > 0:
            rectangles.append(dict(side=side, x=x, y=y, width=width, height=height))
    return dict(canvas_width=target_width, canvas_height=target_height,
                content=dict(x=left, y=top, width=content_w, height=content_h),
                padding=dict(left=left, right=right, top=top, bottom=bottom), rectangles=rectangles)


def crop_decision(size, bbox, target_width=TARGET_W, target_height=TARGET_H):
    """Decide once for audit and resize; never crop on a missing detection."""
    w, h = size
    if w * target_height == h * target_width:
        return {'padded': False, 'reason': 'correct_ratio', 'box': None}
    if bbox is None:
        return {'padded': True, 'reason': 'no_subject_detected', 'box': None}
    xmin, ymin, xmax, ymax = bbox
    if not (0 <= xmin < xmax <= w and 0 <= ymin < ymax <= h):
        return {'padded': True, 'reason': 'invalid_subject_box', 'box': None}
    protected = (max(0, xmin - w * SUBJECT_MARGIN), max(0, ymin - h * SUBJECT_MARGIN),
                 min(w, xmax + w * SUBJECT_MARGIN), min(h, ymax + h * SUBJECT_MARGIN))
    if w * target_height > h * target_width:
        fits = protected[2] - protected[0] <= int(h * target_width / target_height)
    else:
        fits = protected[3] - protected[1] <= int(w * target_height / target_width)
    return {'padded': not fits, 'reason': 'subject_margin' if not fits else 'subject_crop', 'box': protected}


def smart_crop_and_resize(img, bbox, include_geometry=False, target_width=TARGET_W, target_height=TARGET_H):
    def finish(image, padded, geometry=None):
        return (image, padded, geometry) if include_geometry else (image, padded)
    w, h = img.size
    target_ratio = target_width / target_height
    cur_ratio = w / h
    
    decision = crop_decision(img.size, bbox, target_width, target_height)
    if decision['reason'] == 'correct_ratio':
        return finish(img.resize((target_width, target_height), Image.LANCZOS), False)
    protected = decision['box']
    if protected:
        xmin, ymin, xmax, ymax = protected
        cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
        subject_w = xmax - xmin
        subject_h = ymax - ymin
    else:
        cx, cy = w / 2, h / 2
        subject_w, subject_h = 0, 0

    use_padding = decision['padded']

    if cur_ratio > target_ratio:
        # Image is wider than target. We need to crop width.
        crop_w = int(h * target_ratio)
        crop_h = h
        
        if not use_padding:
            left = cx - crop_w / 2
            # clamp
            left = max(0, min(w - crop_w, left))
            img_cropped = img.crop((left, 0, left + crop_w, h))
    else:
        # Image is taller than target. We crop height if the subject fits inside.
        crop_w = w
        crop_h = int(w / target_ratio)
        
        if not use_padding:
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
            bg_h = target_height
            bg_w = int(target_height * bg_ratio)
        else:
            # Scale by width to ensure it covers the target width
            bg_w = target_width
            bg_h = int(target_width / bg_ratio)
            
        bg_img = img.resize((bg_w, bg_h), Image.LANCZOS)
        
        # Center crop the scaled image to exactly target_width x target_height
        bg_left = (bg_w - target_width) // 2
        bg_top = (bg_h - target_height) // 2
        bg_img = bg_img.crop((bg_left, bg_top, bg_left + target_width, bg_top + target_height))
        
        # Apply a minimal Gaussian blur
        bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=5))

        if cur_ratio > target_ratio:
            new_w = target_width
            new_h = int(target_width / cur_ratio)
            img_resized = img.resize((new_w, new_h), Image.LANCZOS)
            bg_img.paste(img_resized, (0, (target_height - new_h) // 2))
            return finish(bg_img, True, padding_geometry(0, (target_height-new_h)//2, new_w, new_h, target_width, target_height))
        else:
            new_h = target_height
            new_w = int(target_height * cur_ratio)
            img_resized = img.resize((new_w, new_h), Image.LANCZOS)
            bg_img.paste(img_resized, ((target_width - new_w) // 2, 0))
            return finish(bg_img, True, padding_geometry((target_width-new_w)//2, 0, new_w, new_h, target_width, target_height))
    else:
        # Standard resize after crop
        return finish(img_cropped.resize((target_width, target_height), Image.LANCZOS), False)

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
