import os
import cv2
import numpy as np
from ultralytics import YOLO
import onnxruntime as ort

WEIGHTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weights')
INPUT_FOLDER = '/home/arrma/Downloads/pool.yolov8/test/images'
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output_onnx_vs_pt')

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

pt_model = YOLO(os.path.join(WEIGHTS_DIR, 'best.pt'))
onnx_session = ort.InferenceSession(os.path.join(WEIGHTS_DIR, 'best.onnx'))

input_name = onnx_session.get_inputs()[0].name
print(f"ONNX input: {input_name}, shape={onnx_session.get_inputs()[0].shape}")
print(f"ONNX outputs: {[(o.name, o.shape) for o in onnx_session.get_outputs()]}")

IMG_SIZE = 640

def letterbox(img, new_shape=(640, 640)):
    shape = img.shape[:2]
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
    dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]
    dw /= 2
    dh /= 2
    if shape[::-1] != new_unpad:
        img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
    return img

def run_onnx(img_bgr):
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    img_lb = letterbox(img_rgb)
    img_lb = img_lb.astype(np.float32) / 255.0
    img_lb = np.transpose(img_lb, (2, 0, 1))
    img_lb = np.expand_dims(img_lb, 0)
    outputs = onnx_session.run(None, {input_name: img_lb})
    return outputs

valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
images = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(valid_extensions)]

for idx, filename in enumerate(images[:10], 1):
    full_input = os.path.join(INPUT_FOLDER, filename)
    img = cv2.imread(full_input)
    if img is None:
        continue

    results_pt = pt_model.predict(source=full_input, conf=0.25, imgsz=IMG_SIZE, verbose=False)
    img_pt = results_pt[0].plot()

    onnx_outputs = run_onnx(img)

    print(f"[{idx}/{len(images)}] {filename}")
    print(f"  PT boxes: {len(results_pt[0].boxes)}")
    print(f"  ONNX outputs shapes: {[o.shape for o in onnx_outputs]}")

    combined = np.hstack([img_pt, img])
    cv2.imwrite(os.path.join(OUTPUT_FOLDER, f"compare_{filename}"), combined)

print(f"\nГотово! Сравнения в {OUTPUT_FOLDER}")
