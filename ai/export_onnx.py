from ultralytics import YOLO

model = YOLO("model/best.pt")

model.export(
    format="onnx",
    imgsz=640,
    opset=12,
    dynamic=False,
    simplify=True
)

print("Export selesai")