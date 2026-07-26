import os
import cv2
import numpy as np


END_POINT = "camera"

RTSP_URL = f"rtsp://10.42.0.1:8554/{END_POINT}"


VIDEO_PATH = RTSP_URL
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_aruco.mp4")

FRAME_DELAY_MS = 1  # задержка между кадрами (мс), 0 = без задержки
PAUSE_ON_DETECT = True  # пауза при обнаружении маркера (e — продолжить)
SHOW_BOUNDING_BOX = True  # показывать bbox и размер в пикселях

# диапазон размера bbox для настоящего маркера (в пикселях)
REAL_MARKER_MIN = 35
REAL_MARKER_MAX = 55
SHOW_ONLY_REAL = True  # показывать только маркеры из диапазона REAL_MARKER_MIN..REAL_MARKER_MAX

# увеличение кадра перед детекцией (помогает ловить мелкие маркеры)
ENABLE_SCALE = False
SCALE_FACTOR = 2  # 2 = удвоение размера

# adaptiveThreshWinSizeStep — шаг окна адаптивной бинаризации.
# Алгоритм сканирует кадр окнами: 3x3, 3+step, 3+2*step, ... до max.
# Чем меньше шаг — тем детальнее сканирование, тем лучше ловит
# деформированные/замаскированные маркеры, но тем медленнее работает.
#
#   Значение | Эффект
#   ---------|----------------------------------------------
#      1     | максимальная точность, самое медленное
#      3     | хорошая точность для маркеров под сеткой
#      5     | баланс скорость/точность
#     10     | по умолчанию в OpenCV, быстрое сканирование
#     20+    | грубое, пропускает мелкие деформации


TRESH_STEP = 3  # при 1 работает очень медленно



DICT_TYPE = cv2.aruco.DICT_4X4_50


class ArucoDetector:
    def __init__(self, dictionary_type=DICT_TYPE, thresh_step=TRESH_STEP):
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary_type)
        self.aruco_params = cv2.aruco.DetectorParameters()

        self.aruco_params.minMarkerPerimeterRate=0.02
        self.aruco_params.adaptiveThreshWinSizeStep = thresh_step

        self.aruco_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        # self.aruco_params.cornerRefinementMaxIterations = 100   нихуя не влияет



        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)

    def detect(self, frame):
        corners, ids, _ = self.detector.detectMarkers(frame)
        return corners, ids

    def draw(self, frame, corners, ids, show_bounding_box=False, only_real=False):
        if ids is None or len(ids) == 0:
            return frame

        cv2.aruco.drawDetectedMarkers(frame, corners, ids)

        for i, marker_id in enumerate(ids.flatten()):
            pts = corners[i][0]

            cx = int(pts[:, 0].mean())
            cy = int(pts[:, 1].mean())

            rect = cv2.minAreaRect(pts.astype(np.float32))
            w, h = rect[1]
            side = max(int(w), int(h))
            is_real = REAL_MARKER_MIN <= side <= REAL_MARKER_MAX

            if only_real and not is_real:
                continue

            if is_real:
                label = f"ID: {marker_id} REAL ({side}px)"
                cv2.putText(frame, label, (cx - 20, cy - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                box = cv2.boxPoints(rect)
                box = np.intp(box)
                cv2.drawContours(frame, [box], 0, (0, 255, 0), 3)
            else:
                label = f"ID: {marker_id}"
                cv2.putText(frame, label, (cx - 20, cy - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

            if show_bounding_box and not is_real:
                box = cv2.boxPoints(rect)
                box = np.intp(box)
                cv2.drawContours(frame, [box], 0, (255, 255, 0), 2)
                print(f"Маркер ID={marker_id}, размер={side}px, центр=({cx}, {cy})")
            elif is_real:
                print(f"РЕАЛЬНЫЙ маркер ID={marker_id}, размер={side}px, центр=({cx}, {cy})")

        return frame


def process_video(input_path, output_path):
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"Не удалось открыть видео: {input_path}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    detector = ArucoDetector(thresh_step=TRESH_STEP)
    frame_count = 0
    detected_count = 0

    print(f"Обработка: {input_path}")
    print(f"Разрешение: {width}x{height}, FPS: {fps}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        detect_frame = frame
        if ENABLE_SCALE:
            detect_frame = cv2.resize(frame, None, fx=SCALE_FACTOR, fy=SCALE_FACTOR, interpolation=cv2.INTER_LINEAR)

        corners, ids = detector.detect(detect_frame)

        if ENABLE_SCALE and ids is not None and len(ids) > 0:
            corners = [c / SCALE_FACTOR for c in corners]

        has_real = False
        if ids is not None and len(ids) > 0:
            detected_count += 1
            if SHOW_ONLY_REAL:
                for c in corners:
                    rect = cv2.minAreaRect(c[0].astype(np.float32))
                    side = max(int(rect[1][0]), int(rect[1][1]))
                    if REAL_MARKER_MIN <= side <= REAL_MARKER_MAX:
                        has_real = True
                        break
            else:
                has_real = True

        result = detector.draw(frame.copy(), corners, ids, show_bounding_box=SHOW_BOUNDING_BOX, only_real=SHOW_ONLY_REAL)
        writer.write(result)

        cv2.imshow("ArUco Detection", result)

        if PAUSE_ON_DETECT and has_real:
            print(f"Маркер обнаружен! Нажми 'e' чтобы продолжить")
            while True:
                key = cv2.waitKey(0) & 0xFF
                if key == ord('e'):
                    break
                elif key == ord('q'):
                    cap.release()
                    writer.release()
                    cv2.destroyAllWindows()
                    return
        else:
            if cv2.waitKey(FRAME_DELAY_MS) & 0xFF == ord('q'):
                break

    cap.release()
    writer.release()
    cv2.destroyAllWindows()

    print(f"Кадров обработано: {frame_count}")
    print(f"Кадров с маркерами: {detected_count}")
    print(f"Результат: {output_path}")


if __name__ == "__main__":
    process_video(VIDEO_PATH, OUTPUT_PATH)
