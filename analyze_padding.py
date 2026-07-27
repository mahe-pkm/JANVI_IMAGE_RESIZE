import os
from pathlib import Path
from PIL import Image
import torch
import torchvision.transforms.functional as F
from torchvision.models.detection import fasterrcnn_resnet50_fpn, FasterRCNN_ResNet50_FPN_Weights
from tqdm import tqdm

SOURCE_DIR = Path(r"c:\Users\rough\Desktop\Logo Processing\May-20261\Resizing")
TARGET_W, TARGET_H = 1200, 1800

def get_model():
    weights = FasterRCNN_ResNet50_FPN_Weights.DEFAULT
    model = fasterrcnn_resnet50_fpn(weights=weights, progress=False)
    model.eval()
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    return model, device

def get_subject_bbox(model, device, img):
    img_tensor = F.to_tensor(img).unsqueeze(0).to(device)
    with torch.no_grad():
        predictions = model(img_tensor)[0]
    
    people = [box.tolist() for box, label, score in zip(predictions['boxes'], predictions['labels'], predictions['scores']) if label == 1 and score > 0.7]
    if not people: return None
    
    largest_box = None
    max_area = 0
    for box in people:
        xmin, ymin, xmax, ymax = box
        area = (xmax - xmin) * (ymax - ymin)
        if area > max_area:
            max_area = area
            largest_box = box
    return largest_box

def needs_padding(img, bbox):
    w, h = img.size
    target_ratio = TARGET_W / TARGET_H
    cur_ratio = w / h
    
    if bbox:
        xmin, ymin, xmax, ymax = bbox
        subject_w = xmax - xmin
        subject_h = ymax - ymin
    else:
        subject_w, subject_h = 0, 0

    if cur_ratio > target_ratio:
        # Image is wider than target. We need to crop width.
        crop_w = int(h * target_ratio)
        if bbox and subject_w > crop_w:
            return True
    else:
        # Image is taller than target. We need to crop height.
        crop_h = int(w / target_ratio)
        if bbox and subject_h > crop_h:
            return True
            
    return False

def main():
    model, device = get_model()
    
    image_paths = []
    for ext in ['*.png', '*.jpg', '*.jpeg']:
        image_paths.extend(list(SOURCE_DIR.rglob(ext)))
        
    print(f"Total images found: {len(image_paths)}")
    
    pad_count = 0
    normal_crop_count = 0
    
    for img_path in tqdm(image_paths):
        try:
            with Image.open(img_path).convert("RGB") as img:
                bbox = get_subject_bbox(model, device, img)
                if needs_padding(img, bbox):
                    pad_count += 1
                else:
                    normal_crop_count += 1
        except Exception as e:
            print(f"Error on {img_path.name}: {e}")
            
    print(f"--- Analysis Complete ---")
    print(f"Total Processed: {pad_count + normal_crop_count}")
    print(f"Images requiring Padding/Generative Fill: {pad_count}")
    print(f"Images perfectly cropped (No filling needed): {normal_crop_count}")

if __name__ == '__main__':
    main()
