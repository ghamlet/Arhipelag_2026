import cv2
import os

BLACK_BOX_DIR = "/home/arrma/PROGRAMMS/Arhipelag_2026/Integration_of_laser_sensor_and_signal_reception_system_into_AUV_&_UAV_system/Qualifying_stage/neural_network_project/dataset/black_box"

count = 0
for folder in sorted(os.listdir(BLACK_BOX_DIR)):
    folder_path = os.path.join(BLACK_BOX_DIR, folder)
    if not os.path.isdir(folder_path):
        continue
    for filename in os.listdir(folder_path):
        name, ext = os.path.splitext(filename)
        if ext.lower() in ('.png', '.jpeg', '.bmp', '.tiff', '.webp'):
            old_path = os.path.join(folder_path, filename)
            new_path = os.path.join(folder_path, name + '.jpg')
            image = cv2.imread(old_path)
            if image is not None:
                cv2.imwrite(new_path, image)
                os.remove(old_path)
                count += 1

print(f"Готово! Сконвертировано: {count} файлов")
