#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
from ai_edge_litert.interpreter import Interpreter
import os
import sys

MODEL_PATH = "/home/arrma/PROGRAMMS/Arhipelag_2026/Integration_of_laser_sensor_and_signal_reception_system_into_AUV_&_UAV_system/Final_stage/OKEANIKA/drone_vision-master/models/model_compatible.tflite"
INPUT_DIR = "/home/arrma/PROGRAMMS/Arhipelag_2026/Integration_of_laser_sensor_and_signal_reception_system_into_AUV_&_UAV_system/Final_stage/OKEANIKA/drone_vision-master/input_images"

print("Загрузка модели...")
interpreter = Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
IMG_HEIGHT, IMG_WIDTH = input_details[0]['shape'][1], input_details[0]['shape'][2]
NUM_CLASSES = output_details[0]['shape'][1]

print(f"Размер входа: {IMG_WIDTH}x{IMG_HEIGHT}, классов: {NUM_CLASSES}")

valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
image_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(valid_extensions)]

if not image_files:
    print(f"В папке {INPUT_DIR} нет изображений!")
    sys.exit(1)

print(f"Найдено изображений: {len(image_files)}")
print("-" * 60)

for img_name in image_files:
    img_path = os.path.join(INPUT_DIR, img_name)
    frame = cv2.imread(img_path)

    if frame is None:
        print(f"[{img_name}] Не удалось прочитать")
        continue

    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (IMG_WIDTH, IMG_HEIGHT))
    input_data = np.expand_dims(resized.astype('float32') / 255.0, axis=0)

    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()

    output_data = interpreter.get_tensor(output_details[0]['index'])[0]
    predicted_digit = np.argmax(output_data)
    confidence = np.max(output_data)

    print(f"[{img_name}] ЦИФРА: {predicted_digit} ({confidence*100:.1f}%)")
    print(f"  Все классы: " + "  ".join([f"{i}:{p*100:.1f}%" for i, p in enumerate(output_data)]))
    print()

print("Готово.")