import time

import cv2
import numpy as np

from pioneer_rknn import Yolo
from pioneer_sdk2 import Camera, CameraType, ImageViewer, ServoCamera

MODEL_NAME = "qwert"

INPUT_WIDTH = 640
INPUT_HEIGHT = 640

OBJECT_THRESHOLD = 0.05
NMS_THRESHOLD = 0.45

STREAM_NAME = "boats_test"
STREAM_FPS = 10

CLASS_NAMES = {
    0: "green",
    1: "orange",
}

CLASS_COLORS = {
    0: (0, 255, 0),
    1: (0, 165, 255),
}


def init_servo(angle: int = -80) -> ServoCamera:
    servo = ServoCamera()
    servo.set_angle(angle)
    return servo


def load_model() -> Yolo:
    print("Загрузка RKNN-модели...")
    return Yolo(
        model_name=MODEL_NAME,
        object_thresh=OBJECT_THRESHOLD,
        nms_thresh=NMS_THRESHOLD,
        img_width=INPUT_WIDTH,
        img_height=INPUT_HEIGHT,
    )


def init_camera() -> Camera:
    print("Запуск камеры...")
    return Camera(camera_type=CameraType.MAIN)


def init_viewer() -> ImageViewer:
    return ImageViewer()


def prepare_input(
    frame: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    display_frame = cv2.resize(
        frame,
        (INPUT_WIDTH, INPUT_HEIGHT),
        interpolation=cv2.INTER_LINEAR,
    )

    rgb_image = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)

    input_tensor = np.expand_dims(rgb_image, axis=0)
    input_tensor = np.ascontiguousarray(input_tensor, dtype=np.uint8)

    return display_frame, input_tensor


def run_detection(
    model: Yolo,
    input_tensor: np.ndarray,
) -> tuple:
    start = time.time()
    result = model.run([input_tensor])
    elapsed = time.time() - start

    boxes = None
    classes = None
    scores = None

    if isinstance(result, (tuple, list)) and len(result) == 3:
        boxes, classes, scores = result
    elif result is not None:
        print("Неожиданный формат результата:", type(result), repr(result))

    return boxes, classes, scores, elapsed


def draw_detections(
    frame: np.ndarray,
    boxes,
    classes,
    scores,
) -> int:
    if boxes is None or classes is None or scores is None:
        return 0

    frame_height, frame_width = frame.shape[:2]
    count = 0

    for box, class_id, score in zip(boxes, classes, scores):
        class_id = int(class_id)
        score = float(score)

        x1, y1, x2, y2 = [int(round(float(v))) for v in box]

        x1 = max(0, min(x1, frame_width - 1))
        y1 = max(0, min(y1, frame_height - 1))
        x2 = max(0, min(x2, frame_width - 1))
        y2 = max(0, min(y2, frame_height - 1))

        if x2 <= x1 or y2 <= y1:
            continue

        class_name = CLASS_NAMES.get(class_id, f"class_{class_id}")
        color = CLASS_COLORS.get(class_id, (255, 255, 255))
        label = f"{class_name}: {score:.2f}"

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame, label,
            (x1, max(25, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA,
        )

        print(
            f"Объект: class={class_name}, id={class_id}, "
            f"score={score:.3f}, box=({x1}, {y1}, {x2}, {y2})"
        )

        count += 1

    return count


def draw_stats(
    frame: np.ndarray,
    detection_count: int,
    inference_time: float,
) -> None:
    cv2.putText(
        frame, f"Objects: {detection_count}",
        (15, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA,
    )
    cv2.putText(
        frame, f"Inference: {inference_time * 1000:.1f} ms",
        (15, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA,
    )


def get_frame(camera: Camera) -> np.ndarray | None:
    frame = camera.get_cv_frame(timeout=2.0)
    if frame is None:
        print("Кадр с камеры не получен")
    return frame


def run_detection_loop(
    camera: Camera,
    viewer: ImageViewer,
    model: Yolo,
) -> None:
    while True:
        frame = get_frame(camera)
        if frame is None:
            continue

        display_frame, input_tensor = prepare_input(frame)
        boxes, classes, scores, elapsed = run_detection(model, input_tensor)

        count = draw_detections(display_frame, boxes, classes, scores)
        draw_stats(display_frame, count, elapsed)

        viewer.imshow(name=STREAM_NAME, frame=display_frame, fps=STREAM_FPS)


def release_resources(
    model: Yolo | None,
    camera: Camera | None,
    viewer: ImageViewer | None,
) -> None:
    print("Освобождение ресурсов...")

    for obj, name, stop_fn in [
        (model, "модели", "release"),
        (camera, "камеры", "stop"),
        (viewer, "потока", "close"),
    ]:
        if obj is not None:
            try:
                getattr(obj, stop_fn)()
            except Exception as e:
                print(f"Ошибка освобождения {name}: {e}")

    print("Готово")


def main() -> None:
    model = None
    camera = None
    viewer = None

    try:
        init_servo()
        camera = init_camera()
        viewer = init_viewer()
        model = load_model()
        run_detection_loop(camera, viewer, model)

    except KeyboardInterrupt:
        print("\nОстановлено пользователем")

    except Exception as error:
        print(f"\nОшибка: {type(error).__name__}: {error}")
        raise

    finally:
        release_resources(model, camera, viewer)


if __name__ == "__main__":
    main()
