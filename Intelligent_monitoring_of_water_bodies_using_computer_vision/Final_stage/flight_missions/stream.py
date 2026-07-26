import cv2

RTSP_URL = "rtsp://10.42.0.1:8554/pioneer_camera"

cap = cv2.VideoCapture(RTSP_URL)
if not cap.isOpened():
    raise RuntimeError(f"Не удалось открыть RTSP-поток: {RTSP_URL}")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        cv2.imshow("Drone Stream", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
