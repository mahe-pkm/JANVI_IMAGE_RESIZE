from ultralytics import YOLO
import sys

def main():
    image_path = r"C:\Users\rough\Desktop\Logo Processing\May-20261\Resizing\16-may-2026\Amber glow_selected_images\Amber glow_front_full_view.png"
    
    # Load YOLOv8 model
    model = YOLO('yolov8n.pt') # n is nano, fast and usually accurate enough
    
    # Run inference
    results = model(image_path)
    
    print("\n--- YOLOv8 Detections ---")
    for r in results:
        boxes = r.boxes
        for box in boxes:
            # class 0 is 'person' in COCO
            if int(box.cls[0]) == 0:
                coords = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                print(f"Person detected with confidence {conf:.2f}: {coords}")

if __name__ == "__main__":
    main()
