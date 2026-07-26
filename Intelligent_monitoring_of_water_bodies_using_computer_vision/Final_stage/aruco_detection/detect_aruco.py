import os
import cv2

VIDEO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "4.mp4")
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_aruco.mp4")

FRAME_DELAY_MS = 1  # задержка между кадрами (мс), 0 = без задержки
PAUSE_ON_DETECT = True  # пауза при обнаружении маркера (e — продолжить)

DICT_TYPE = cv2.aruco.DICT_4X4_50


class ArucoDetector:
    def __init__(self, dictionary_type=DICT_TYPE, thresh_step=4):
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary_type)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.aruco_params.adaptiveThreshWinSizeStep = thresh_step  # шаг окна бинаризации (по умолч. 10)
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)

    def detect(self, frame):
        corners, ids, _ = self.detector.detectMarkers(frame)
        return corners, ids

    def draw(self, frame, corners, ids):
        if ids is None or len(ids) == 0:
            return frame

        cv2.aruco.drawDetectedMarkers(frame, corners, ids)

        for i, marker_id in enumerate(ids.flatten()):
            cx = int(corners[i][0][:, 0].mean())
            cy = int(corners[i][0][:, 1].mean())
            label = f"ID: {marker_id}"
            cv2.putText(frame, label, (cx - 20, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

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

    detector = ArucoDetector()
    frame_count = 0
    detected_count = 0

    print(f"Обработка: {input_path}")
    print(f"Разрешение: {width}x{height}, FPS: {fps}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        corners, ids = detector.detect(frame)

        if ids is not None and len(ids) > 0:
            detected_count += 1

        result = detector.draw(frame.copy(), corners, ids)
        writer.write(result)

        cv2.imshow("ArUco Detection", result)

        if PAUSE_ON_DETECT and ids is not None and len(ids) > 0:
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
