#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ai_edge_litert.interpreter import Interpreter
import numpy as np

print("Загрузка модели...")
interpreter = Interpreter(model_path="/home/arrma/PROGRAMMS/Arhipelag_2026/Integration_of_laser_sensor_and_signal_reception_system_into_AUV_&_UAV_system/Final_stage/OKEANIKA/drone_vision-master/models/model_compatible.tflite")
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print(f" Модель загружена успешно!")
print(f"Входной размер: {input_details[0]['shape']}")
print(f"Выходной размер: {output_details[0]['shape']}")

test_input = np.random.rand(1, 64, 64, 3).astype(np.float32)
interpreter.set_tensor(input_details[0]['index'], test_input)
interpreter.invoke()
output = interpreter.get_tensor(output_details[0]['index'])

print(f" Тестовый прогон успешен!")
print(f"Результат: {output}")
print(f"Предсказанная цифра: {np.argmax(output[0])}")
