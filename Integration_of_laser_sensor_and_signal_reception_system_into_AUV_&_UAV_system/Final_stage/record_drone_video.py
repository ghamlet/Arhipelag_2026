#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для записи видео с камеры дрона на самом дроне.
Сохраняет в /usr/local/drone_ros/src/drone/scripts/examples/records
"""

import cv2
import os
import time
from datetime import datetime

CAMERA_INDEX = 0
RECORD_DIR = '/usr/local/drone_ros/src/drone/scripts/examples/records'
FPS = 20.0

os.makedirs(RECORD_DIR, exist_ok=True)

cap = cv2.VideoCapture(CAMERA_INDEX)
if not cap.isOpened():
    print("ОШИБКА: Не удалось открыть камеру!")
    exit()

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filename = f'record_{timestamp}.mp4'
filepath = os.path.join(RECORD_DIR, filename)

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
writer = cv2.VideoWriter(filepath, fourcc, FPS, (width, height))

if not writer.isOpened():
    print("ОШИБКА: Не удалось создать видеофайл!")
    cap.release()
    exit()

print(f"Запись начата: {filepath}")
print("Нажмите Ctrl+C для остановки...")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        writer.write(frame)
except KeyboardInterrupt:
    print("\nОстановка записи...")
finally:
    writer.release()
    cap.release()
    print(f"Видео сохранено: {filepath}")