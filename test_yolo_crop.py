from subject_aware_resize import get_model, get_subject_bbox, smart_crop_and_resize
from PIL import Image

def main():
    image_path = r"E:\Long gown\Glam Garne_selected_images (2)\regen_Glam Garnet Lon_back_closeup_20260527_112039.png"
    
    print("Loading model...")
    model, device = get_model()
    
    print(f"Processing image: {image_path}")
    with Image.open(image_path).convert("RGB") as img:
        print(f"Original size: {img.size}")
        bbox = get_subject_bbox(model, device, img)
        print(f"YOLO bbox: {bbox}")
        
        result_img, used_pad = smart_crop_and_resize(img, bbox)
        
        print(f"Used Padding: {used_pad}")
        print(f"Output size: {result_img.size}")

if __name__ == "__main__":
    main()
