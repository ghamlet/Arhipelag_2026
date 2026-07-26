import os
import cv2
import numpy as np

VIDEO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "4.mp4")

# минимальное количество фиксаций маркера чтобы считать его найденным
CONFIRM_THRESHOLD = 5

# диапазон размера bbox для настоящего маркера (в пикселях)
REAL_MARKER_MIN = 35
REAL_MARKER_MAX = 55

ENABLE_SCALE = False
SCALE_FACTOR = 2

TRESH_STEP = 3

DICT_TYPE = cv2.aruco.DICT_4X4_50


class MarkerStats:
    def __init__(self, confirm_threshold):
        self.detections = {}  # id -> количество фиксаций
        self.confirmed = set()  # id -> уже подтверждённые
        self.threshold = confirm_threshold

    def update(self, ids, corners):
        if ids is None:
            return

        for i, marker_id in enumerate(ids.flatten()):
            pts = corners[i][0]
            rect = cv2.minAreaRect(pts.astype(np.float32))
            side = max(int(rect[1][0]), int(rect[1][1]))

            if not (REAL_MARKER_MIN <= side <= REAL_MARKER_MAX):
                continue

            marker_id = int(marker_id)
            self.detections[marker_id] = self.detections.get(marker_id, 0) + 1

            if marker_id not in self.confirmed and self.detections[marker_id] >= self.threshold:
                self.confirmed.add(marker_id)
                print(f"[+] Маркер ID={marker_id} ПОДТВЕРЖДЁН! (фикаций: {self.detections[marker_id]})")

    def summary(self):
        print("\n===== ИТОГИ =====")
        print(f"Уникальных маркеров обнаружено: {len(self.detections)}")
        for mid, count in sorted(self.detections.items()):
            status = "ПОДТВЕРЖДЁН" if mid in self.confirmed else "недостаточно фиксаций"
            print(f"  ID={mid}: {count} фиксаций — {status}")
        print(f"Подтверждённых: {len(self.confirmed)}/{self.threshold}+")
        print("=================\n")


def main():
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"Не удалось открыть видео: {VIDEO_PATH}")
        return

    aruco_dict = cv2.aruco.getPredefinedDictionary(DICT_TYPE)
    params = cv2.aruco.DetectorParameters()
    params.adaptiveThreshWinSizeStep = TRESH_STEP
    detector = cv2.aruco.ArucoDetector(aruco_dict, params)

    stats = MarkerStats(CONFIRM_THRESHOLD)
    frame_count = 0

    print(f"Видео: {VIDEO_PATH}")
    print(f"Порог подтверждения: {CONFIRM_THRESHOLD} фиксаций")
    print(f"Диапазон размера: {REAL_MARKER_MIN}..{REAL_MARKER_MAX}px")
    print()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        detect_frame = frame
        if ENABLE_SCALE:
            detect_frame = cv2.resize(frame, None, fx=SCALE_FACTOR, fy=SCALE_FACTOR, interpolation=cv2.INTER_LINEAR)

        corners, ids, _ = detector.detectMarkers(detect_frame)

        if ENABLE_SCALE and ids is not None and len(ids) > 0:
            corners = [c / SCALE_FACTOR for c in corners]

        stats.update(ids, corners)

        cv2.aruco.drawDetectedMarkers(frame, corners, ids)

        cv2.imshow("Marker Counter", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    stats.summary()


if __name__ == "__main__":
    main()
