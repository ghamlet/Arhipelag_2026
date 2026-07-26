import os
import cv2
from datetime import datetime
from pioneer_sdk2 import Camera, CameraType

RECORDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "records")
os.makedirs(RECORDS_DIR, exist_ok=True)

RTSP_URL = "rtsp://10.42.0.1:8554/camera"


def connect_stream(url: str) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        raise RuntimeError(f"Не удалось открыть RTSP-поток: {url}")
    return cap


def get_stream_params(cap: cv2.VideoCapture) -> tuple[int, int, int]:
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    return width, height, fps


def create_writer(width: int, height: int, fps: int) -> tuple[cv2.VideoWriter, str]:
    filename = f"drone_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    filepath = os.path.join(RECORDS_DIR, filename)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
    return writer, filepath


def draw_overlay(frame, recording: bool) -> None:
    label = "REC" if recording else "VIEW"
    color = (0, 0, 255) if recording else (0, 255, 0)
    cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)


def main() -> None:
    cap = connect_stream(RTSP_URL)
    width, height, fps = get_stream_params(cap)

    writer = None
    recording = False

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            if recording and writer is not None:
                writer.write(frame)

            draw_overlay(frame, recording)
            cv2.imshow("Drone Stream", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                if not recording:
                    writer, filepath = create_writer(width, height, fps)
                    recording = True
                    print(f"Запись начата: {filepath}")
                else:
                    recording = False
                    writer.release()
                    writer = None
                    print("Запись остановлена")

    finally:
        if writer is not None:
            writer.release()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
