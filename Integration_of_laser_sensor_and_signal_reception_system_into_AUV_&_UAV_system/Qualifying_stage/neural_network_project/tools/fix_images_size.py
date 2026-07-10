import os
import cv2

# ==========================================
# УКАЖИТЕ СВОИ ПУТИ К ПАПКАМ ЗДЕСЬ:
# ==========================================
INPUT_FOLDER = "/home/arrma/PROGRAMMS/Arhipelag_2026/Integration_of_laser_sensor_and_signal_reception_system_into_AUV_&_UAV_system/Qualifying_stage/neural_network_project/dataset/no_object"    # Папка с исходными фотками
OUTPUT_FOLDER = "/home/arrma/PROGRAMMS/Arhipelag_2026/Integration_of_laser_sensor_and_signal_reception_system_into_AUV_&_UAV_system/Qualifying_stage/neural_network_project/dataset/no_object_fix_size"  # Папка, куда сохранятся исправленные фотки

# Целевой размер
TARGET_WIDTH = 800
TARGET_HEIGHT = 600

# Создаем папку для результатов, если её нет
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
count_ok = 0
count_resized = 0

print("⏳ Начинаю проверку и обработку изображений...\n")

for filename in os.listdir(INPUT_FOLDER):
    if not filename.lower().endswith(valid_extensions):
        continue

    input_path = os.path.join(INPUT_FOLDER, filename)
    output_path = os.path.join(OUTPUT_FOLDER, filename)

    img = cv2.imread(input_path)
    if img is None:
        print(f"❌ Ошибка чтения файла: {filename}")
        continue

    height, width, _ = img.shape

    if width == TARGET_WIDTH and height == TARGET_HEIGHT:
        cv2.imwrite(output_path, img)
        count_ok += 1
    else:
        resized_img = cv2.resize(img, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_CUBIC)
        cv2.imwrite(output_path, resized_img)
        count_resized += 1
        print(f"🔄 {filename}: {width}x{height} -> {TARGET_WIDTH}x{TARGET_HEIGHT}")

print("\n" + "="*40)
print("🎉 Обработка завершена!")
print(f"✅ Уже были {TARGET_WIDTH}x{TARGET_HEIGHT}: {count_ok}")
print(f"🔄 Приведены к {TARGET_WIDTH}x{TARGET_HEIGHT}: {count_resized}")
print(f"📁 Результат в: {OUTPUT_FOLDER}")
print("="*40)
