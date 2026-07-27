import torch
import torchvision
from torchvision.models.detection import fasterrcnn_resnet50_fpn, FasterRCNN_ResNet50_FPN_Weights
from torchvision.transforms import functional as F
from PIL import Image
import sys

def test_detection(img_path):
    print("Loading model...")
    weights = FasterRCNN_ResNet50_FPN_Weights.DEFAULT
    model = fasterrcnn_resnet50_fpn(weights=weights, progress=False)
    model.eval()

    print(f"Loading image {img_path}...")
    img = Image.open(img_path).convert("RGB")
    img_tensor = F.to_tensor(img).unsqueeze(0)

    print("Running detection...")
    with torch.no_grad():
        predictions = model(img_tensor)

    pred = predictions[0]
    # Filter by person class (label 1 in COCO) and score > 0.8
    people = [(box.tolist(), score.item()) for box, label, score in zip(pred['boxes'], pred['labels'], pred['scores']) if label == 1 and score > 0.8]
    
    print(f"Found {len(people)} people.")
    for box, score in people:
        print(f"Box: {box}, Score: {score}")

if __name__ == '__main__':
    test_detection('c:/Users/rough/Desktop/Logo Processing/May-20261/Resizing/16-may-2026/Amber glow_selected_images/Amber glow_front_full_view.png')
