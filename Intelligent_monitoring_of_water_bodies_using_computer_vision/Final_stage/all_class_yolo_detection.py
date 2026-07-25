
import cv2
import numpy as np
from pioneer_rknn import Yolo
from pioneer_sdk2 import Camera, ImageViewer, CameraType

# Глобальные переменные — изображения и результаты детекции
image_1 = None
image_2 = None
object_1 = None
object_2 = None

# Список классов объектов (содержит все возможные объекты в YOLO)
classNames = ["green", "orange"]

def resize_img(img):
    """
    Изменяет размер изображения до IMG_SIZE и добавляет ось batch

    Args:
        img (numpy.ndarray): Исходное изображение

    Returns:
        numpy.ndarray: Изображение с размером IMG_SIZE и добавленной осью batch
    """
    # Изменяем размер изображения до IMG_SIZE
    img_copy = cv2.resize(img, IMG_SIZE)

    # Добавляем ось batch (для RKNN)
    img_copy = np.expand_dims(img_copy, 0)
    return img_copy

def yolo_find_on_image(img, results, classNames, class_filter=None, score_thr=None):
    """
    Фильтрует результаты детекции YOLO по классам и уверенности

    Args:
        img (numpy.ndarray): Исходное изображение
        results (tuple): Результаты детекции (boxes, classes, scores)
        classNames (list): Список названий классов
        class_filter (list or None): Список классов для фильтрации
        score_thr (float or None): Порог уверенности

    Returns:
        dict: Фильтрованные результаты детекции
    """
    boxes, classes, scores = results # Распаковываем результаты

    # Если нет данных — возвращаем пустой словарь
    if boxes is None or classes is None or scores is None or len(boxes) == 0:
        return {
            "boxes": np.zeros((0, 4), dtype=np.float32),
            "classes": np.zeros((0,), dtype=np.int32),
            "scores": np.zeros((0,), dtype=np.float32),
            "orig_shape": img.shape[:2],
            "classNames": classNames
        }

    # Преобразуем данные в массивы NumPy
    boxes = np.array(boxes)
    classes = np.array(classes)
    scores = np.array(scores)

    indices = np.arange(len(boxes))  # Индексы всех детекций

     # Фильтрация по классам (если указано)
    if class_filter is not None:
        allowed = [classNames.index(cls_name) for cls_name in class_filter if cls_name in classNames]
        indices = [i for i in indices if classes[i] in allowed]

    # Фильтрация по уверенности (если указано)
    if score_thr is not None:
        indices = [i for i in indices if scores[i] >= score_thr]

    # Возвращаем фильтрованные данные
    return {
        "boxes": boxes[indices],
        "classes": classes[indices],
        "scores": scores[indices],
        "orig_shape": img.shape[:2],
        "classNames": classNames
    }

def draw_yolo_on_image(img, yolo_obj, color=(0,255,0), thickness=2):
    """
    Отрисовывает детекции YOLO на изображении

    Args:
        img (numpy.ndarray): Изображение для отрисовки
        yolo_obj (dict): Результаты детекции
        color (tuple): Цвет рамки
        thickness (int): Толщина линии
    """
    boxes = yolo_obj["boxes"]
    classes = yolo_obj["classes"]
    classNames = yolo_obj["classNames"]
    orig_h, orig_w = yolo_obj["orig_shape"]

     # Множители для масштабирования координат
    scale_x = orig_w / IMG_SIZE[0]
    scale_y = orig_h / IMG_SIZE[1]

    # Отрисовываем каждую детекцию
    for box, cl in zip(boxes, classes):
        left, top, right, bottom = [int(coord) for coord in box] # Координаты бокса
        
        # Масштабируем координаты к оригинальному изображению
        left   = int(left * scale_x)
        right  = int(right * scale_x)
        top    = int(top * scale_y)
        bottom = int(bottom * scale_y)

        # Рисуем рамку
        cv2.rectangle(img, (left, top), (right, bottom), color, thickness)
        
        # Рисуем надпись
        label = f"{classNames[cl]}"
        cv2.putText(img, label, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

# Инициализация камер
cam_main, cam_opt = Camera(camera_type=CameraType.MAIN), Camera(camera_type=CameraType.OPT)

iv = ImageViewer() # Инициализация отображения изображений

def hex_to_bgr(hex_color: str) -> tuple[int, int, int]:
    """
    Преобразует HEX-цвет в BGR (OpenCV формат)

    Args:
        hex_color (str): HEX цвет в формате #RRGGBB

    Returns:
        tuple[int, int, int]: Цвет в формате BGR
    """
    # Убираем символ #
    if hex_color.startswith("#"):
        hex_color = hex_color[1:]

    # Проверяем длину
    if len(hex_color) != 6:
        raise ValueError("Hex color must be in format #RRGGBB")

    # Преобразуем HEX в BGR
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    return (b, g, r)


if __name__ == "__main__":
    print("Выбрана модель:Yolo")
    IMG_SIZE = (640, 640)

    # Загрузка модели Yolo
    model = Yolo(model_name="qwert")
    while True:
        # Получаем кадры с камер
        image_1 = cam_main.get_cv_frame()

        # Выполняем детекцию на первом и втором кадре по всем классам
        object_1 = yolo_find_on_image(image_1, results_image_1 := model.run([resize_img(image_1)]), classNames, class_filter=None)

        # Отрисовываем детекции
        draw_yolo_on_image(image_1, object_1, hex_to_bgr("#ff4040"))

        # Отображаем изображения
        iv.imshow(name='first', frame=image_1)
