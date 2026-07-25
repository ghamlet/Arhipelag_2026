import cv2
from datetime import datetime


def main():
    rtsp_url = "rtsp://10.42.0.1:8554/camera"
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        print(f"Не удалось открыть RTSP-поток: {rtsp_url}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = None
    recording = False

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            if recording and writer is not None:
                writer.write(frame)

            label = "REC" if recording else "VIEW"
            color = (0, 0, 255) if recording else (0, 255, 0)
            cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

            cv2.imshow("Drone Stream (OpenCV)", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                if not recording:
                    filename = f"drone_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                    writer = cv2.VideoWriter(filename, fourcc, fps, (width, height))
                    recording = True
                    print(f"Запись начата: {filename}")
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
