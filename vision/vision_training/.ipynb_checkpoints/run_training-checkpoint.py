import os
from ultralytics import YOLO

def main():
    print("--- YOLOv8 Automated Human Training ---")
    
    # 1. Load the pre-trained Nano model
    model = YOLO("yolov8n.pt")
    
    # 2. Train on humans only
    print("Starting training (Humans only)...")
    model.train(
        data="coco8.yaml",
        epochs=10,
        imgsz=640,
        classes=[0],
        exist_ok=True
    )
    
    # 3. Export to ONNX (Better for RPi 5 Python 3.13)
    print("Exporting to ONNX...")
    export_path = model.export(format="onnx", int8=True)
    
    print(f"DONE! Model at: {export_path}")
    
if __name__ == "__main__":
    main()
