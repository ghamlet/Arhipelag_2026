import os
import cv2
from ultralytics import YOLO

# 1. Настройки путей (измени на свои)
# Если файлы лежат в папке со скриптом, можно написать просто 'best.pt'
MODEL_PATH = '/home/arrma/PROGRAMMS/Arhipelag_2026/Intelligent_monitoring_of_water_bodies_using_computer_vision/Final_stage/weights/best.pt'  
INPUT_FOLDER = '/home/arrma/Downloads/pool.yolov8/test/images'  # Откуда брать фото
OUTPUT_FOLDER = '/home/arrma/PROGRAMMS/Arhipelag_2026/Intelligent_monitoring_of_water_bodies_using_computer_vision/Final_stage/output'      # Куда сохранять результат

# 2. Создаем папку для результатов, если её нет
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 3. Загружаем модель YOLOv8
model = YOLO(MODEL_PATH)

# Список поддерживаемых расширений
valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')

# 4. Сканируем папку и запускаем цикл по всем файлам
print("Начало обработки изображений...")
images = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(valid_extensions)]

if not images:
    print(f"❌ В папке {INPUT_FOLDER} не найдено подходящих картинок!")
else:
    for idx, filename in enumerate(images, 1):
        full_input_path = os.path.join(INPUT_FOLDER, filename)
        
        # Запускаем распознавание (conf=0.25 — порог уверенности)
        # verbose=False отключает лишний спам в консоли для каждого кадра
        results = model.predict(source=full_input_path, conf=0.25, imgsz=640, verbose=False)
        
        # Получаем картинку с нарисованными рамками
        annotated_img = results[0].plot()
        
        # Сохраняем размеченный кадр в выходную папку
        full_output_path = os.path.join(OUTPUT_FOLDER, f"detected_{filename}")
        cv2.imwrite(full_output_path, annotated_img)
        
        print(f"[{idx}/{len(images)}] Обработан файл: {filename} -> Сохранен как detected_{filename}")

    print(f"🎉 Готово! Все результаты сохранены в папку: {OUTPUT_FOLDER}")
