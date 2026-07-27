from pioneer_sdk2 import Pioneer, Camera, ImageViewer, ServoCamera
import time
import select
import sys
import cv2
import numpy as np

servo = ServoCamera()
servo.set_angle(-80)

ALTITUDE = 1.8

# подстройка под камеру: сколько пикселей на метр при высоте ALTITUDE
# измерить empirically: посчитать пиксели оранжевого квадрата известного размера
# формула: PX_PER_M = (IMAGE_WIDTH / (2 * ALTITUDE * tan(HFOV/2)))
# Pioneer typical: HFOV ~ 96 deg, IMAGE_WIDTH ~ 640
PX_PER_M = 100  # пикселей на метр (подобрать экспериментально)

# HSV диапазон оранжевого
ORANGE_H_MIN = 5
ORANGE_H_MAX = 20
ORANGE_S_MIN = 100
ORANGE_S_MAX = 255
ORANGE_V_MIN = 100
ORANGE_V_MAX = 255

# порог площади контура чтобы считать объект валидным
MIN_CONTOUR_AREA = 500

HOVER_MODE = "input"
HOVER_SECONDS = 15

waypoints = [
    (-2.9, 0.8),
    (-3.1, 0.8)
]

drone = Pioneer()
camera = Camera()
viewer = ImageViewer()

current_point_label = None


def hover(seconds=None, mode=None):
    if mode is None:
        mode = HOVER_MODE

    if mode == "input":
        print("Напиши 'yes' чтобы продолжить...")
        try:
            while True:
                show_camera()
                if select.select([sys.stdin], [], [], 0)[0]:
                    line = sys.stdin.readline().strip()
                    if line == "yes":
                        break
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("Остановка, посадка")
            drone.land()
    else:
        t = seconds if seconds is not None else HOVER_SECONDS
        end_time = time.time() + t
        while time.time() < end_time:
            show_camera()
            time.sleep(0.1)


def show_camera():
    frame = camera.get_cv_frame(timeout=1.0)
    if frame is not None:
        if current_point_label:
            cv2.putText(frame, current_point_label, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        viewer.imshow("pioneer_camera", frame)


def wait_for_point():
    while not drone.point_reached():
        time.sleep(0.1)


def find_orange_center(frame):
    """Находит центр оранжевого объекта в кадре. Возвращает (cx, cy) в пикселях или None."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv,
                       np.array([ORANGE_H_MIN, ORANGE_S_MIN, ORANGE_V_MIN]),
                       np.array([ORANGE_H_MAX, ORANGE_S_MAX, ORANGE_V_MAX]))
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < MIN_CONTOUR_AREA:
        return None

    M = cv2.moments(largest)
    if M["m00"] == 0:
        return None

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    return cx, cy


def correct_position():
    """Считывает кадр, находит оранжевый объект, вычисляет смещение и летит туда."""
    global current_point_label

    frame = camera.get_cv_frame(timeout=1.0)
    if frame is None:
        print("Не удалось получить кадр")
        return

    h, w = frame.shape[:2]
    center_x, center_y = w // 2, h // 2

    result = find_orange_center(frame)
    if result is None:
        print("Оранжевый объект не найден")
        return

    cx, cy = result
    dx_px = cx - center_x  # смещение по X в пикселях (вправо +)
    dy_px = cy - center_y  # смещение по Y в пикселях (вниз +)

    dx_m = dx_px / PX_PER_M
    dy_m = dy_px / PX_PER_M

    print(f"Объект в ({cx}, {cy}), центр кадра ({center_x}, {center_y})")
    print(f"Смещение: {dx_px}px / {dx_m:.2f}m по X, {dy_px}px / {dy_m:.2f}m по Y")

    # body_fixed: x — вперёд/назад, y — влево/вправо
    # dy_px > 0 значит объект ниже центра → дрон должен лететь назад (x отрицательный)
    # dx_px > 0 значит объект правее центра → дрон должен лететь вправо (y положительный)
    drone_x = -dy_m
    drone_y = dx_m

    print(f"go_to_local_point_body_fixed: x={drone_x:.2f}, y={drone_y:.2f}")
    drone.go_to_local_point_body_fixed(x=drone_x, y=drone_y, z=0, yaw=0, time=3)
    wait_for_point()
    print("Корректировка завершена")


try:
    drone.arm()
    time.sleep(3)
    drone.takeoff()
    time.sleep(3)

    for i, (x, y) in enumerate(waypoints):
        print(f"Летим в точку {i+1}/{len(waypoints)}: x={x}, y={y}, z={ALTITUDE}")
        drone.go_to_local_point(x=x, y=y, z=ALTITUDE, yaw=0, time=5)
        wait_for_point()
        current_point_label = f"Point {i+1}: x={x}, y={y}"
        print(f"Точка {i+1} достигнута!")
        hover()

    print("Возвращаемся домой")
    current_point_label = "Home"
    drone.go_to_local_point(x=0, y=0, z=ALTITUDE, yaw=0, time=5)
    wait_for_point()

    print("Поиск оранжевой площадки...")
    time.sleep(2)
    correct_position()

    drone.land()

except KeyboardInterrupt:
    print("Остановка, посадка")
    drone.land()

except Exception as error:
    print("Ошибка:", error)
    drone.land()

finally:
    viewer.close()
    camera.stop()
    drone.close_connection()
