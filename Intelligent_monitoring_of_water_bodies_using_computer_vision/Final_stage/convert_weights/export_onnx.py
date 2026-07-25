import os
from ultralytics import YOLO

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_DIR = os.path.join(BASE_DIR, '..', 'weights')

MODEL_PATH = os.path.join(WEIGHTS_DIR, 'best_2.pt')

model = YOLO(MODEL_PATH)
model.export(format='onnx', opset=12, simplify=True)
print(f"Модель экспортирована: {os.path.join(WEIGHTS_DIR, 'best.onnx')}")
