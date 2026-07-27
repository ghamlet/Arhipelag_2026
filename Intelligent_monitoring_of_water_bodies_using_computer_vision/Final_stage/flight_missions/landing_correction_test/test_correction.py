import cv2
import numpy as np
import glob
import os

FRAME_W = 1080
FRAME_H = 720

# камера на высоте 1м видит 1×1м
VIEW_W_M = 1.0
VIEW_H_M = 1.0

PX_PER_M_X = FRAME_W / VIEW_W_M  # 1080
PX_PER_M_Y = FRAME_H / VIEW_H_M  # 720

# HSV диапазон оранжевого
ORANGE_H_MIN = 5
ORANGE_H_MAX = 20
ORANGE_S_MIN = 100
ORANGE_S_MAX = 255
ORANGE_V_MIN = 100
ORANGE_V_MAX = 255

MIN_CONTOUR_AREA = 500

TEST_DIR = os.path.dirname(os.path.abspath(__file__))


def find_orange_center(frame):
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


def main():
    images = sorted(glob.glob(os.path.join(TEST_DIR, "*.jpg")) +
                    glob.glob(os.path.join(TEST_DIR, "*.png")) +
                    glob.glob(os.path.join(TEST_DIR, "*.bmp")))

    if not images:
        print("Нет изображений в папке")
        return

    print(f"Найдено {len(images)} изображений")

    centers = []
    for path in images:
        frame = cv2.imread(path)
        if frame is None:
            continue
        frame = cv2.resize(frame, (FRAME_W, FRAME_H))
        result = find_orange_center(frame)
        if result:
            cx, cy = result
            centers.append((cx, cy))
            print(f"  {os.path.basename(path)}: ({cx}, {cy})")
        else:
            print(f"  {os.path.basename(path)}: объект не найден")

    if not centers:
        print("Объект не найден ни на одном кадре")
        return

    avg_cx = np.mean([c[0] for c in centers])
    avg_cy = np.mean([c[1] for c in centers])

    center_x = FRAME_W / 2  # 540
    center_y = FRAME_H / 2  # 360

    dx_px = avg_cx - center_x
    dy_px = avg_cy - center_y

    dx_m = dx_px / PX_PER_M_X
    dy_m = dy_px / PX_PER_M_Y

    print(f"\n=== РЕЗУЛЬТАТ ===")
    print(f"Средний центр объекта: ({avg_cx:.1f}, {avg_cy:.1f})")
    print(f"Центр кадра: ({center_x}, {center_y})")
    print(f"Смещение: {dx_px:.1f}px / {dx_m:.3f}m по X, {dy_px:.1f}px / {dy_m:.3f}m по Y")
    print(f"Система координат: X вправо, Y вверх")
    drone_x = dx_m       # вправо — положительный X
    drone_y = -dy_m      # вверх в drone = минус вниз в image
    print(f"Для go_to_local_point_body_fixed:")
    print(f"  x = {drone_x:.3f}  (вправо/влево)")
    print(f"  y = {drone_y:.3f}  (вверх/вниз)")

    # визуализация на последнем кадре
    last_frame = cv2.imread(images[-1])
    last_frame = cv2.resize(last_frame, (FRAME_W, FRAME_H))
    cv2.circle(last_frame, (int(avg_cx), int(avg_cy)), 10, (0, 0, 255), -1)
    cv2.circle(last_frame, (int(center_x), int(center_y)), 10, (0, 255, 0), 2)
    cv2.line(last_frame, (int(center_x), int(center_y)), (int(avg_cx), int(avg_cy)), (255, 0, 0), 2)
    cv2.imshow("Result", last_frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
