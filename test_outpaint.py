import torch
from diffusers import AutoPipelineForInpainting
from PIL import Image, ImageDraw
import torchvision.transforms.functional as F
from torchvision.models.detection import fasterrcnn_resnet50_fpn, FasterRCNN_ResNet50_FPN_Weights

# Configuration
TARGET_W, TARGET_H = 1200, 1800
PROMPT = "seamless studio photography background, high quality, highly detailed, soft lighting"
NEG_PROMPT = "blurry, weird artifacts, extra limbs, human, body parts, deformed, text, watermark"

def get_bbox(img):
    weights = FasterRCNN_ResNet50_FPN_Weights.DEFAULT
    model = fasterrcnn_resnet50_fpn(weights=weights, progress=False).to('cuda').eval()
    img_tensor = F.to_tensor(img).unsqueeze(0).to('cuda')
    with torch.no_grad():
        predictions = model(img_tensor)[0]
    people = [box.tolist() for box, label, score in zip(predictions['boxes'], predictions['labels'], predictions['scores']) if label == 1 and score > 0.7]
    if not people: return None
    
    # Largest
    largest_box = None
    max_area = 0
    for box in people:
        xmin, ymin, xmax, ymax = box
        area = (xmax - xmin) * (ymax - ymin)
        if area > max_area:
            max_area = area
            largest_box = box
    return largest_box

def prepare_image_and_mask(img_path):
    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    
    bbox = get_bbox(img)
    target_ratio = TARGET_W / TARGET_H
    cur_ratio = w / h
    
    if cur_ratio > target_ratio:
        new_w = TARGET_W
        new_h = int(TARGET_W / cur_ratio)
        img_resized = img.resize((new_w, new_h), Image.LANCZOS)
        
        # Padded image
        final_img = Image.new("RGB", (TARGET_W, TARGET_H), (255, 255, 255))
        y_offset = (TARGET_H - new_h) // 2
        final_img.paste(img_resized, (0, y_offset))
        
        # Mask
        mask = Image.new("L", (TARGET_W, TARGET_H), 255) # White is what we want to generate
        draw = ImageDraw.Draw(mask)
        draw.rectangle([0, y_offset, TARGET_W, y_offset + new_h], fill=0) # Black is what we keep
    else:
        new_h = TARGET_H
        new_w = int(TARGET_H * cur_ratio)
        img_resized = img.resize((new_w, new_h), Image.LANCZOS)
        
        final_img = Image.new("RGB", (TARGET_W, TARGET_H), (255, 255, 255))
        x_offset = (TARGET_W - new_w) // 2
        final_img.paste(img_resized, (x_offset, 0))
        
        mask = Image.new("L", (TARGET_W, TARGET_H), 255)
        draw = ImageDraw.Draw(mask)
        draw.rectangle([x_offset, 0, x_offset + new_w, TARGET_H], fill=0)
        
    return final_img, mask

def run_outpaint():
    img_path = r"c:\Users\rough\Desktop\Logo Processing\May-20261\Resizing\16-may-2026\Amber glow_selected_images\Amber glow_front_full_view.png"
    
    print("1. Preparing image and mask...")
    padded_img, mask_img = prepare_image_and_mask(img_path)
    
    print("2. Loading SDXL Inpainting Model (This will take a few minutes on the first run)...")
    pipeline = AutoPipelineForInpainting.from_pretrained(
        "diffusers/stable-diffusion-xl-1.0-inpainting-0.1", torch_dtype=torch.float16, variant="fp16"
    ).to("cuda")
    
    print("3. Generating background...")
    result = pipeline(
        prompt=PROMPT,
        negative_prompt=NEG_PROMPT,
        image=padded_img,
        mask_image=mask_img,
        guidance_scale=8.0,
        num_inference_steps=30,  # steps
        strength=0.99  # very strong inpainting
    ).images[0]
    
    output_path = r"c:\Users\rough\Desktop\Logo Processing\May-20261\test_outpaint_result.png"
    result.save(output_path)
    print(f"Done! Saved to {output_path}")

if __name__ == '__main__':
    run_outpaint()
