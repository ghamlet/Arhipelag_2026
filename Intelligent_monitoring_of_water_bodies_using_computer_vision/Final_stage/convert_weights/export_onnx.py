from ultralytics import YOLO

MODEL_PATH = '../weights/best.pt'
EXPORT_FORMAT = 'onnx'
OPSET = 12

model = YOLO(MODEL_PATH)
model.export(format=EXPORT_FORMAT, opset=OPSET)
print(f"Модель экспортирована в {MODEL_PATH.replace('.pt', '.onnx')}")
