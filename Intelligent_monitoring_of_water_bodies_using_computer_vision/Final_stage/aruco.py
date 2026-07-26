"""YOLOv8 RKNN + ArUco для Geoscan Pioneer Mini 2.

Функции:
- детекция и классификация судов через pioneer_rknn.Yolo;
- поиск ArUco только рядом с YOLO-рамками;
- накопительное подтверждение уникального судна по ArUco ID;
- накопительное определение класса судна;
- поток с рамками через ImageViewer;
- запись обработанного видео на бортовой компьютер;
- итоговый отчёт в терминале после Ctrl+C или ошибки.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from pioneer_rknn import Yolo
from pioneer_sdk2 import Camera, CameraType, ImageViewer, ServoCamera


# ============================================================
# ОСНОВНЫЕ НАСТРОЙКИ
# ============================================================

MODEL_NAME = "qwert"

INPUT_WIDTH = 640
INPUT_HEIGHT = 640

OBJECT_THRESHOLD = 0.60
NMS_THRESHOLD = 0.45

STREAM_NAME = "boats_test"
STREAM_FPS = 10
SERVO_ANGLE = -80

# ВАЖНО: порядок должен совпадать с data.yaml.
# Предполагается: 0 = зарегистрированное, 1 = незарегистрированное.
DISPLAY_CLASS_NAMES = {
    0: "registered",
    1: "unregistered",
}

TERMINAL_CLASS_NAMES = {
    0: "зарегистрированное",
    1: "незарегистрированное",
}

# Цвета BGR.
CLASS_COLORS = {
    0: (0, 255, 0),      # зелёный
    1: (0, 165, 255),    # оранжевый
}

UNKNOWN_COLOR = (255, 255, 255)
PENDING_COLOR = (0, 255, 255)
ARUCO_COLOR = (255, 0, 255)
PANEL_COLOR = (0, 0, 0)


# ============================================================
# ARUCO
# ============================================================

ARUCO_DICTIONARY = "DICT_4X4_50"

# Когда известны реальные ID, перечисли их здесь, например {0, 1, 2, 3, 4, 5}.
# Пустое множество разрешает все ID словаря.
ALLOWED_ARUCO_IDS: set[int] = set()

# ArUco ищется только около лодок, найденных YOLO.
ARUCO_ROI_MARGIN = 0.20
ARUCO_UPSCALE_FACTOR = 3.0

# Подтверждение уникального ID по нескольким кадрам.
MIN_ARUCO_CONFIRMATIONS = 3
MIN_CLASS_MATCHES = 3
ARUCO_CONFIRMATION_WINDOW = 30  # 30 кадров ~= 3 секунды при 10 FPS
MIN_DRAW_OCCURRENCES = 2

# Допуск положения маркера относительно YOLO-рамки.
RELATIVE_CENTER_MIN = -0.20
RELATIVE_CENTER_MAX = 1.20
RELATIVE_CENTER_SPREAD = 0.45

# Уже подтверждённый класс меняется только при заметном перевесе.
CLASS_CHANGE_MARGIN = 0.15

# Фильтр геометрии маркера в координатах исходного ROI.
MIN_MARKER_SIDE_PX = 6.0
MAX_SIDE_RATIO = 2.0
MAX_DIAGONAL_RATIO = 2.0
MIN_MARKER_AREA_RATIO = 0.0005
MAX_MARKER_AREA_RATIO = 0.30


# ============================================================
# ВИДЕОЗАПИСЬ
# ============================================================

OUTPUT_DIRECTORY = Path("/home/pioneermini/workspace")
OUTPUT_BASENAME = "flight_result"
OUTPUT_FPS = 10.0


# ============================================================
# ПОДГОТОВКА ВХОДА RKNN
# ============================================================


def prepare_input(frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Возвращает BGR-кадр 640x640 и RGB NHWC uint8 с batch-размерностью."""

    display_frame = cv2.resize(
        frame,
        (INPUT_WIDTH, INPUT_HEIGHT),
        interpolation=cv2.INTER_LINEAR,
    )

    rgb_image = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
    input_tensor = np.expand_dims(rgb_image, axis=0)
    input_tensor = np.ascontiguousarray(input_tensor, dtype=np.uint8)

    return display_frame, input_tensor


# ============================================================
# YOLO
# ============================================================


def clamp_box(
    box: Any,
    frame_width: int,
    frame_height: int,
) -> tuple[int, int, int, int] | None:
    try:
        x1, y1, x2, y2 = [int(round(float(value))) for value in box]
    except (TypeError, ValueError):
        return None

    x1 = max(0, min(x1, frame_width - 1))
    y1 = max(0, min(y1, frame_height - 1))
    x2 = max(0, min(x2, frame_width - 1))
    y2 = max(0, min(y2, frame_height - 1))

    if x2 <= x1 or y2 <= y1:
        return None

    return x1, y1, x2, y2


def normalize_yolo_result(result: Any, frame: np.ndarray) -> list[dict[str, Any]]:
    """Преобразует (boxes, classes, scores) в список словарей."""

    if not isinstance(result, (tuple, list)) or len(result) != 3:
        return []

    boxes, classes, scores = result
    if boxes is None or classes is None or scores is None:
        return []

    frame_height, frame_width = frame.shape[:2]
    detections: list[dict[str, Any]] = []

    for index, (box, class_id, score) in enumerate(zip(boxes, classes, scores)):
        normalized_box = clamp_box(box, frame_width, frame_height)
        if normalized_box is None:
            continue

        class_id = int(class_id)
        score = float(score)

        detections.append(
            {
                "index": index,
                "box": normalized_box,
                "class_id": class_id,
                "confidence": score,
            }
        )

    return detections


def expand_box(
    box: tuple[int, int, int, int],
    frame_width: int,
    frame_height: int,
    margin: float,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    width = x2 - x1
    height = y2 - y1

    dx = width * margin
    dy = height * margin

    expanded = clamp_box(
        (x1 - dx, y1 - dy, x2 + dx, y2 + dy),
        frame_width,
        frame_height,
    )
    return expanded if expanded is not None else box


# ============================================================
# ARUCO: ДЕТЕКТОР И ПРЕДОБРАБОТКА
# ============================================================


def set_parameter_if_available(parameters: Any, name: str, value: Any) -> None:
    if hasattr(parameters, name):
        setattr(parameters, name, value)


def create_aruco_detector() -> Any:
    if not hasattr(cv2, "aruco"):
        raise RuntimeError("В установленной сборке OpenCV отсутствует cv2.aruco")

    if not hasattr(cv2.aruco, ARUCO_DICTIONARY):
        raise RuntimeError(f"Словарь ArUco не найден: {ARUCO_DICTIONARY}")

    dictionary = cv2.aruco.getPredefinedDictionary(
        getattr(cv2.aruco, ARUCO_DICTIONARY)
    )

    if hasattr(cv2.aruco, "DetectorParameters"):
        parameters = cv2.aruco.DetectorParameters()
    else:
        parameters = cv2.aruco.DetectorParameters_create()

    # Умеренно строгие параметры. Полный кадр не сканируется, поэтому сетка
    # значительно реже превращается в ложный маркер.
    parameter_values = {
        "adaptiveThreshWinSizeMin": 3,
        "adaptiveThreshWinSizeMax": 31,
        "adaptiveThreshWinSizeStep": 4,
        "adaptiveThreshConstant": 7,
        "minMarkerPerimeterRate": 0.03,
        "maxMarkerPerimeterRate": 1.5,
        "polygonalApproxAccuracyRate": 0.04,
        "minCornerDistanceRate": 0.05,
        "minDistanceToBorder": 2,
        "perspectiveRemovePixelPerCell": 8,
        "perspectiveRemoveIgnoredMarginPerCell": 0.13,
        "errorCorrectionRate": 0.35,
        "maxErroneousBitsInBorderRate": 0.25,
        "useAruco3Detection": False,
    }

    for name, value in parameter_values.items():
        set_parameter_if_available(parameters, name, value)

    if (
        hasattr(parameters, "cornerRefinementMethod")
        and hasattr(cv2.aruco, "CORNER_REFINE_SUBPIX")
    ):
        parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX

    if hasattr(cv2.aruco, "ArucoDetector"):
        return cv2.aruco.ArucoDetector(dictionary, parameters)

    return dictionary, parameters


def detect_markers_on_image(image: np.ndarray, detector: Any) -> tuple[Any, Any]:
    if hasattr(detector, "detectMarkers"):
        corners, ids, _ = detector.detectMarkers(image)
    else:
        dictionary, parameters = detector
        corners, ids, _ = cv2.aruco.detectMarkers(
            image,
            dictionary,
            parameters=parameters,
        )

    return corners, ids


def create_aruco_variants(upscaled_roi: np.ndarray) -> list[tuple[str, np.ndarray]]:
    gray = cv2.cvtColor(upscaled_roi, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(
        clipLimit=1.5,
        tileGridSize=(8, 8),
    )
    clahe_image = clahe.apply(gray)

    return [
        ("gray", gray),
        ("clahe", clahe_image),
    ]


def marker_geometry_is_valid(
    corners: np.ndarray,
    roi_width: int,
    roi_height: int,
) -> bool:
    try:
        corners = np.asarray(corners, dtype=np.float32).reshape(4, 2)
    except (TypeError, ValueError):
        return False

    if not np.all(np.isfinite(corners)):
        return False

    sides = [
        float(np.linalg.norm(corners[(index + 1) % 4] - corners[index]))
        for index in range(4)
    ]
    min_side = min(sides)
    max_side = max(sides)

    if min_side < MIN_MARKER_SIDE_PX:
        return False
    if max_side / max(min_side, 1e-6) > MAX_SIDE_RATIO:
        return False

    diagonals = [
        float(np.linalg.norm(corners[2] - corners[0])),
        float(np.linalg.norm(corners[3] - corners[1])),
    ]
    if max(diagonals) / max(min(diagonals), 1e-6) > MAX_DIAGONAL_RATIO:
        return False

    contour = corners.reshape(-1, 1, 2)
    if not cv2.isContourConvex(contour):
        return False

    area = abs(float(cv2.contourArea(contour)))
    roi_area = max(1.0, float(roi_width * roi_height))
    area_ratio = area / roi_area

    return MIN_MARKER_AREA_RATIO <= area_ratio <= MAX_MARKER_AREA_RATIO


def get_marker_center(corners: np.ndarray) -> tuple[float, float]:
    corners = np.asarray(corners, dtype=np.float32).reshape(4, 2)
    return float(np.mean(corners[:, 0])), float(np.mean(corners[:, 1]))


def get_marker_area(corners: np.ndarray) -> float:
    contour = np.asarray(corners, dtype=np.float32).reshape(-1, 1, 2)
    return abs(float(cv2.contourArea(contour)))


def detect_aruco_in_detection(
    frame: np.ndarray,
    detection: dict[str, Any],
    detector: Any,
) -> list[dict[str, Any]]:
    """Ищет ArUco в расширенной YOLO-рамке и возвращает координаты полного кадра."""

    frame_height, frame_width = frame.shape[:2]
    search_box = expand_box(
        detection["box"],
        frame_width,
        frame_height,
        ARUCO_ROI_MARGIN,
    )
    detection["aruco_search_box"] = search_box

    x1, y1, x2, y2 = search_box
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return []

    upscaled_roi = cv2.resize(
        roi,
        None,
        fx=ARUCO_UPSCALE_FACTOR,
        fy=ARUCO_UPSCALE_FACTOR,
        interpolation=cv2.INTER_CUBIC,
    )

    roi_height, roi_width = roi.shape[:2]
    candidates: list[dict[str, Any]] = []

    for source_name, variant in create_aruco_variants(upscaled_roi):
        corners_list, ids = detect_markers_on_image(variant, detector)
        if ids is None or len(ids) == 0:
            continue

        for marker_id, marker_corners in zip(ids.flatten(), corners_list):
            marker_id = int(marker_id)

            if ALLOWED_ARUCO_IDS and marker_id not in ALLOWED_ARUCO_IDS:
                continue

            local_corners = (
                np.asarray(marker_corners, dtype=np.float32).reshape(4, 2)
                / ARUCO_UPSCALE_FACTOR
            )

            if not marker_geometry_is_valid(local_corners, roi_width, roi_height):
                continue

            global_corners = local_corners.copy()
            global_corners[:, 0] += x1
            global_corners[:, 1] += y1

            candidates.append(
                {
                    "id": marker_id,
                    "corners": global_corners,
                    "center": get_marker_center(global_corners),
                    "area": get_marker_area(global_corners),
                    "source": source_name,
                    "detection_index": detection["index"],
                }
            )

    # Один ID мог быть найден на gray и CLAHE. Оставляем вариант большей площади.
    best_by_id: dict[int, dict[str, Any]] = {}
    for marker in candidates:
        marker_id = marker["id"]
        previous = best_by_id.get(marker_id)
        if previous is None or marker["area"] > previous["area"]:
            best_by_id[marker_id] = marker

    return list(best_by_id.values())


# ============================================================
# СОПОСТАВЛЕНИЕ ARUCO И YOLO
# ============================================================


def point_in_box(
    point: tuple[float, float],
    box: tuple[int, int, int, int],
) -> bool:
    x, y = point
    x1, y1, x2, y2 = box
    return x1 <= x <= x2 and y1 <= y <= y2


def box_center(box: tuple[int, int, int, int]) -> tuple[float, float]:
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def normalized_marker_center(
    marker: dict[str, Any],
    detection: dict[str, Any],
) -> tuple[float, float]:
    marker_x, marker_y = marker["center"]
    x1, y1, x2, y2 = detection["box"]
    width = max(1.0, float(x2 - x1))
    height = max(1.0, float(y2 - y1))
    return (marker_x - x1) / width, (marker_y - y1) / height


def relative_center_is_reasonable(center: tuple[float, float]) -> bool:
    x, y = center
    return (
        RELATIVE_CENTER_MIN <= x <= RELATIVE_CENTER_MAX
        and RELATIVE_CENTER_MIN <= y <= RELATIVE_CENTER_MAX
    )


def collect_and_match_markers(
    frame: np.ndarray,
    detections: list[dict[str, Any]],
    detector: Any,
) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    """Возвращает уникальные маркеры кадра и соответствие detection_index -> match."""

    all_candidates: list[dict[str, Any]] = []

    for detection in detections:
        try:
            all_candidates.extend(
                detect_aruco_in_detection(frame, detection, detector)
            )
        except Exception as error:
            print(
                "Предупреждение: ошибка ArUco для YOLO-рамки "
                f"{detection['index']}: {type(error).__name__}: {error}"
            )

    # Для каждого физического ID выбираем одно лучшее сопоставление на кадре.
    best_match_by_id: dict[int, dict[str, Any]] = {}

    for marker in all_candidates:
        candidates: list[tuple[int, float, float, dict[str, Any]]] = []

        for detection in detections:
            search_box = detection.get("aruco_search_box") or expand_box(
                detection["box"],
                frame.shape[1],
                frame.shape[0],
                ARUCO_ROI_MARGIN,
            )

            if not point_in_box(marker["center"], search_box):
                continue

            relative_center = normalized_marker_center(marker, detection)
            if not relative_center_is_reasonable(relative_center):
                continue

            marker_x, marker_y = marker["center"]
            center_x, center_y = box_center(detection["box"])
            distance = float(np.hypot(marker_x - center_x, marker_y - center_y))

            # Сначала предпочитаем центр внутри обычной YOLO-рамки.
            outside_normal_box = 0 if point_in_box(marker["center"], detection["box"]) else 1
            candidates.append(
                (
                    outside_normal_box,
                    distance,
                    -float(detection["confidence"]),
                    detection,
                )
            )

        if not candidates:
            continue

        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        detection = candidates[0][3]
        match = {
            "marker": marker,
            "detection": detection,
            "relative_center": normalized_marker_center(marker, detection),
        }

        previous = best_match_by_id.get(marker["id"])
        if previous is None:
            best_match_by_id[marker["id"]] = match
            continue

        # При дубликате ID выбираем более крупный маркер, затем более уверенную YOLO-рамку.
        previous_key = (
            previous["marker"]["area"],
            previous["detection"]["confidence"],
        )
        current_key = (marker["area"], detection["confidence"])
        if current_key > previous_key:
            best_match_by_id[marker["id"]] = match

    # Одной YOLO-рамке разрешаем только один ID: самый крупный маркер.
    matches_by_detection: dict[int, dict[str, Any]] = {}
    for match in best_match_by_id.values():
        detection_index = match["detection"]["index"]
        previous = matches_by_detection.get(detection_index)
        if previous is None or match["marker"]["area"] > previous["marker"]["area"]:
            matches_by_detection[detection_index] = match

    accepted_ids = {
        match["marker"]["id"] for match in matches_by_detection.values()
    }
    markers = [
        match["marker"]
        for match in matches_by_detection.values()
        if match["marker"]["id"] in accepted_ids
    ]

    return markers, matches_by_detection


# ============================================================
# РЕЕСТР УНИКАЛЬНЫХ СУДОВ
# ============================================================


def create_vessel_entry(aruco_id: int, frame_number: int) -> dict[str, Any]:
    return {
        "aruco_id": aruco_id,
        "occurrences": 0,
        "matches": 0,
        "registered_score": 0.0,
        "unregistered_score": 0.0,
        "registered_frames": 0,
        "unregistered_frames": 0,
        "first_seen_frame": frame_number,
        "last_seen_frame": frame_number,
        "best_confidence": 0.0,
        "final_class_id": None,
        "confirmed": False,
        "reported": False,
        "recent_observations": [],  # (frame_number, relative_x, relative_y)
    }


def trim_recent_observations(vessel: dict[str, Any], frame_number: int) -> None:
    minimum_frame = frame_number - ARUCO_CONFIRMATION_WINDOW
    vessel["recent_observations"] = [
        observation
        for observation in vessel["recent_observations"]
        if observation[0] >= minimum_frame
    ]


def recent_centers_are_consistent(vessel: dict[str, Any]) -> bool:
    observations = vessel["recent_observations"]
    if len(observations) < MIN_ARUCO_CONFIRMATIONS:
        return False

    xs = [observation[1] for observation in observations]
    ys = [observation[2] for observation in observations]

    return (
        max(xs) - min(xs) <= RELATIVE_CENTER_SPREAD
        and max(ys) - min(ys) <= RELATIVE_CENTER_SPREAD
    )


def candidate_class(vessel: dict[str, Any]) -> int | None:
    if vessel["registered_score"] > vessel["unregistered_score"]:
        return 0
    if vessel["unregistered_score"] > vessel["registered_score"]:
        return 1
    if vessel["registered_frames"] > vessel["unregistered_frames"]:
        return 0
    if vessel["unregistered_frames"] > vessel["registered_frames"]:
        return 1
    return vessel["final_class_id"]


def update_final_class(vessel: dict[str, Any]) -> bool:
    """Возвращает True, если класс уже подтверждённого судна изменился."""

    previous_class = vessel["final_class_id"]
    new_class = candidate_class(vessel)

    if new_class is None:
        return False

    if previous_class is None:
        vessel["final_class_id"] = new_class
        return False

    if new_class == previous_class:
        return False

    if vessel["confirmed"]:
        previous_score = (
            vessel["registered_score"]
            if previous_class == 0
            else vessel["unregistered_score"]
        )
        new_score = (
            vessel["registered_score"]
            if new_class == 0
            else vessel["unregistered_score"]
        )
        if new_score <= previous_score * (1.0 + CLASS_CHANGE_MARGIN):
            return False

    vessel["final_class_id"] = new_class
    return True


def update_vessel_registry(
    vessels: dict[int, dict[str, Any]],
    matches_by_detection: dict[int, dict[str, Any]],
    frame_number: int,
) -> list[tuple[int, int]]:
    """Обновляет реестр; один ID учитывается максимум один раз за кадр."""

    class_change_events: list[tuple[int, int]] = []
    seen_ids: set[int] = set()

    for match in matches_by_detection.values():
        marker = match["marker"]
        detection = match["detection"]
        aruco_id = int(marker["id"])

        if aruco_id in seen_ids:
            continue
        seen_ids.add(aruco_id)

        vessel = vessels.setdefault(
            aruco_id,
            create_vessel_entry(aruco_id, frame_number),
        )

        class_id = int(detection["class_id"])
        confidence = float(detection["confidence"])
        relative_x, relative_y = match["relative_center"]

        vessel["occurrences"] += 1
        vessel["matches"] += 1
        vessel["last_seen_frame"] = frame_number
        vessel["best_confidence"] = max(vessel["best_confidence"], confidence)
        vessel["recent_observations"].append(
            (frame_number, relative_x, relative_y)
        )
        trim_recent_observations(vessel, frame_number)

        if class_id == 0:
            vessel["registered_score"] += confidence
            vessel["registered_frames"] += 1
        elif class_id == 1:
            vessel["unregistered_score"] += confidence
            vessel["unregistered_frames"] += 1

        was_confirmed = vessel["confirmed"]
        class_changed = update_final_class(vessel)

        # После подтверждения судно не становится неподтверждённым, когда покидает кадр.
        if not vessel["confirmed"]:
            vessel["confirmed"] = (
                len(vessel["recent_observations"]) >= MIN_ARUCO_CONFIRMATIONS
                and vessel["matches"] >= MIN_CLASS_MATCHES
                and recent_centers_are_consistent(vessel)
                and vessel["final_class_id"] is not None
            )

        if (
            was_confirmed
            and vessel["confirmed"]
            and class_changed
            and vessel["final_class_id"] is not None
        ):
            class_change_events.append((aruco_id, vessel["final_class_id"]))

    return class_change_events


def get_vessel_statistics(vessels: dict[int, dict[str, Any]]) -> dict[str, int]:
    confirmed = [vessel for vessel in vessels.values() if vessel["confirmed"]]
    registered = sum(
        1 for vessel in confirmed if vessel["final_class_id"] == 0
    )
    unregistered = sum(
        1 for vessel in confirmed if vessel["final_class_id"] == 1
    )

    return {
        "unique": len(confirmed),
        "registered": registered,
        "unregistered": unregistered,
        "pending": len(vessels) - len(confirmed),
    }


# ============================================================
# ОТРИСОВКА
# ============================================================


def text_color_for_background(background: tuple[int, int, int]) -> tuple[int, int, int]:
    blue, green, red = background
    brightness = 0.114 * blue + 0.587 * green + 0.299 * red
    return (0, 0, 0) if brightness > 140 else (255, 255, 255)


def draw_text(
    frame: np.ndarray,
    text: str,
    position: tuple[int, int],
    background: tuple[int, int, int] = PANEL_COLOR,
    scale: float = 0.52,
    thickness: int = 2,
) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    (text_width, text_height), baseline = cv2.getTextSize(
        text,
        font,
        scale,
        thickness,
    )

    frame_height, frame_width = frame.shape[:2]
    x = max(4, min(int(position[0]), max(4, frame_width - text_width - 8)))
    y = max(text_height + 8, min(int(position[1]), frame_height - baseline - 4))

    cv2.rectangle(
        frame,
        (x - 4, y - text_height - baseline - 4),
        (x + text_width + 4, y + baseline + 4),
        background,
        -1,
    )
    cv2.putText(
        frame,
        text,
        (x, y),
        font,
        scale,
        text_color_for_background(background),
        thickness,
        cv2.LINE_AA,
    )


def draw_marker(frame: np.ndarray, marker: dict[str, Any]) -> None:
    corners = np.asarray(marker["corners"], dtype=np.int32).reshape(4, 2)
    center = tuple(np.mean(corners, axis=0).astype(int))

    cv2.polylines(frame, [corners], True, ARUCO_COLOR, 2)
    cv2.circle(frame, center, 4, ARUCO_COLOR, -1)
    draw_text(
        frame,
        f"ID:{marker['id']}",
        (center[0] + 6, center[1] - 6),
        ARUCO_COLOR,
        scale=0.46,
    )


def draw_detection(
    frame: np.ndarray,
    detection: dict[str, Any],
    match: dict[str, Any] | None,
    vessels: dict[int, dict[str, Any]],
) -> None:
    x1, y1, x2, y2 = detection["box"]
    class_id = int(detection["class_id"])
    confidence = float(detection["confidence"])
    color = CLASS_COLORS.get(class_id, UNKNOWN_COLOR)

    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    detected_class = DISPLAY_CLASS_NAMES.get(class_id, f"class_{class_id}")

    if match is None:
        label = f"ID:? | {detected_class} | {confidence:.2f}"
        draw_text(frame, label, (x1, y1 - 7), color)
        return

    aruco_id = int(match["marker"]["id"])
    vessel = vessels.get(aruco_id)

    if vessel is None or vessel["occurrences"] < MIN_DRAW_OCCURRENCES:
        label = f"ID:? | {detected_class} | {confidence:.2f}"
        draw_text(frame, label, (x1, y1 - 7), color)
        return

    if vessel["confirmed"] and vessel["final_class_id"] is not None:
        final_class = DISPLAY_CLASS_NAMES.get(
            int(vessel["final_class_id"]),
            f"class_{vessel['final_class_id']}",
        )
        label = f"ID:{aruco_id} | {final_class} | {confidence:.2f}"
    else:
        recent_count = len(vessel["recent_observations"])
        label = (
            f"ID:{aruco_id} | candidate "
            f"{min(recent_count, MIN_ARUCO_CONFIRMATIONS)}/{MIN_ARUCO_CONFIRMATIONS}"
        )

    draw_text(frame, label, (x1, y1 - 7), color)


def draw_statistics(
    frame: np.ndarray,
    processing_fps: float,
    detections_count: int,
    markers_count: int,
    vessels: dict[int, dict[str, Any]],
) -> None:
    stats = get_vessel_statistics(vessels)

    lines = [
        f"FPS: {processing_fps:.1f}",
        f"YOLO: {detections_count}",
        f"ArUco: {markers_count}",
        f"Unique: {stats['unique']}",
        f"Registered: {stats['registered']}",
        f"Unregistered: {stats['unregistered']}",
        f"Pending: {stats['pending']}",
    ]

    y = 25
    for line in lines:
        draw_text(frame, line, (10, y), PANEL_COLOR, scale=0.50)
        y += 24


# ============================================================
# ТЕРМИНАЛ И ОТЧЁТ
# ============================================================


def terminal_class_name(class_id: int | None) -> str:
    if class_id is None:
        return "класс не определён"
    return TERMINAL_CLASS_NAMES.get(class_id, f"неизвестный класс {class_id}")


def print_new_events(
    vessels: dict[int, dict[str, Any]],
    class_change_events: list[tuple[int, int]],
) -> None:
    for aruco_id, vessel in sorted(vessels.items()):
        if not vessel["confirmed"] or vessel["reported"]:
            continue

        print(
            f"Обнаружено: {terminal_class_name(vessel['final_class_id'])} судно, "
            f"ArUco ID: {aruco_id}, "
            f"confidence: {vessel['best_confidence']:.2f}, "
            f"совпадений: {vessel['matches']}"
        )
        vessel["reported"] = True

    for aruco_id, class_id in class_change_events:
        print(
            f"Обновлён класс: ArUco ID {aruco_id} — "
            f"{terminal_class_name(class_id)} судно"
        )


def print_final_report(
    vessels: dict[int, dict[str, Any]],
    processed_frames: int,
    average_fps: float,
    video_path: Path | None,
) -> None:
    confirmed = sorted(
        [vessel for vessel in vessels.values() if vessel["confirmed"]],
        key=lambda vessel: vessel["aruco_id"],
    )
    candidates = sorted(
        [vessel for vessel in vessels.values() if not vessel["confirmed"]],
        key=lambda vessel: vessel["aruco_id"],
    )

    registered = sum(
        1 for vessel in confirmed if vessel["final_class_id"] == 0
    )
    unregistered = sum(
        1 for vessel in confirmed if vessel["final_class_id"] == 1
    )

    print()
    print("==================================================")
    print("ИТОГОВЫЙ ОТЧЁТ")
    print("==================================================")
    print(f"Обработано кадров: {processed_frames}")
    print(f"Средний FPS обработки: {average_fps:.1f}")
    print(f"Всего уникальных подтверждённых судов: {len(confirmed)}")
    print(f"Зарегистрированных: {registered}")
    print(f"Незарегистрированных: {unregistered}")
    print()
    print("Суда:")

    if confirmed:
        for number, vessel in enumerate(confirmed, start=1):
            print(
                f"{number}. ArUco ID {vessel['aruco_id']} — "
                f"{terminal_class_name(vessel['final_class_id'])} судно, "
                f"confidence: {vessel['best_confidence']:.2f}, "
                f"совпадений: {vessel['matches']}"
            )
    else:
        print("Подтверждённые суда не найдены.")

    if candidates:
        print()
        print("Неподтверждённые кандидаты:")
        for vessel in candidates:
            print(
                f"ArUco ID {vessel['aruco_id']} — "
                f"обнаружений: {vessel['occurrences']}, "
                f"совпадений с YOLO: {vessel['matches']}"
            )

    if video_path is not None:
        print()
        print(f"Видео с детекцией сохранено: {video_path}")

    print("==================================================")


# ============================================================
# VIDEOWRITER
# ============================================================


def create_video_writer() -> tuple[Any | None, Path | None]:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    mp4_path = OUTPUT_DIRECTORY / f"{OUTPUT_BASENAME}_{timestamp}.mp4"
    writer = cv2.VideoWriter(
        str(mp4_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        OUTPUT_FPS,
        (INPUT_WIDTH, INPUT_HEIGHT),
    )

    if writer.isOpened():
        return writer, mp4_path

    writer.release()

    avi_path = OUTPUT_DIRECTORY / f"{OUTPUT_BASENAME}_{timestamp}.avi"
    writer = cv2.VideoWriter(
        str(avi_path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        OUTPUT_FPS,
        (INPUT_WIDTH, INPUT_HEIGHT),
    )

    if writer.isOpened():
        return writer, avi_path

    writer.release()
    return None, None


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    camera = None
    viewer = None
    model = None
    servo_camera = None
    writer = None
    writer_path: Path | None = None

    vessels: dict[int, dict[str, Any]] = {}
    frame_number = 0
    total_processing_time = 0.0

    try:
        print("Инициализация сервопривода камеры...")
        servo_camera = ServoCamera()
        servo_result = servo_camera.set_angle(SERVO_ANGLE)
        print(f"Угол камеры: {SERVO_ANGLE}, результат: {servo_result}")

        print("Создание ArUco-детектора...")
        aruco_detector = create_aruco_detector()
        print(f"Словарь ArUco: {ARUCO_DICTIONARY}")

        print("Запуск камеры...")
        camera = Camera(camera_type=CameraType.MAIN)
        viewer = ImageViewer()

        print("Загрузка RKNN-модели...")
        model = Yolo(
            model_name=MODEL_NAME,
            object_thresh=OBJECT_THRESHOLD,
            nms_thresh=NMS_THRESHOLD,
            img_width=INPUT_WIDTH,
            img_height=INPUT_HEIGHT,
        )

        writer, writer_path = create_video_writer()
        if writer is None:
            print("Предупреждение: VideoWriter не открылся; работа продолжится без записи.")
        else:
            print(f"Запись видео: {writer_path}")

        print("Модель загружена.")
        print(f"Модель: {MODEL_NAME}")
        print(f"Порог YOLO: {OBJECT_THRESHOLD}")
        print(f"Поток: http://10.42.0.1:8889/{STREAM_NAME}/")
        print("Для завершения нажмите Ctrl+C.")

        first_frame = True

        while True:
            frame = camera.get_cv_frame(timeout=2.0)
            if frame is None:
                print("Кадр с камеры не получен")
                continue

            loop_started = time.perf_counter()
            frame_number += 1

            display_frame, input_tensor = prepare_input(frame)

            if first_frame:
                print(
                    "Вход RKNN:",
                    input_tensor.shape,
                    input_tensor.dtype,
                    f"range={int(input_tensor.min())}...{int(input_tensor.max())}",
                )
                first_frame = False

            result = model.run([input_tensor])
            detections = normalize_yolo_result(result, display_frame)

            markers, matches_by_detection = collect_and_match_markers(
                display_frame,
                detections,
                aruco_detector,
            )

            class_change_events = update_vessel_registry(
                vessels,
                matches_by_detection,
                frame_number,
            )
            print_new_events(vessels, class_change_events)

            for marker in markers:
                vessel = vessels.get(int(marker["id"]))
                if vessel is not None and (
                    vessel["confirmed"]
                    or vessel["occurrences"] >= MIN_DRAW_OCCURRENCES
                ):
                    draw_marker(display_frame, marker)

            for detection in detections:
                draw_detection(
                    display_frame,
                    detection,
                    matches_by_detection.get(detection["index"]),
                    vessels,
                )

            processing_time = time.perf_counter() - loop_started
            total_processing_time += processing_time
            processing_fps = 1.0 / processing_time if processing_time > 0 else 0.0

            draw_statistics(
                display_frame,
                processing_fps,
                len(detections),
                len(markers),
                vessels,
            )

            if writer is not None:
                try:
                    writer.write(display_frame)
                except Exception as error:
                    print(
                        "Предупреждение: ошибка записи кадра: "
                        f"{type(error).__name__}: {error}"
                    )

            viewer.imshow(
                name=STREAM_NAME,
                frame=display_frame,
                fps=STREAM_FPS,
            )

            if frame_number % 10 == 0:
                stats = get_vessel_statistics(vessels)
                print(
                    f"Кадр {frame_number} | "
                    f"YOLO: {len(detections)} | "
                    f"ArUco: {len(markers)} | "
                    f"уникальных: {stats['unique']} | "
                    f"FPS: {processing_fps:.1f}"
                )

    except KeyboardInterrupt:
        print("\nОстановлено пользователем")

    except Exception as error:
        print(f"\nОшибка: {type(error).__name__}: {error}")
        raise

    finally:
        print("Освобождение ресурсов...")

        if writer is not None:
            try:
                writer.release()
            except Exception as error:
                print(f"Ошибка закрытия видео: {error}")

        if model is not None:
            try:
                model.release()
            except Exception as error:
                print(f"Ошибка освобождения модели: {error}")

        if camera is not None:
            try:
                camera.stop()
            except Exception as error:
                print(f"Ошибка остановки камеры: {error}")

        if viewer is not None:
            try:
                viewer.close()
            except Exception as error:
                print(f"Ошибка закрытия потока: {error}")

        if servo_camera is not None and hasattr(servo_camera, "close"):
            try:
                servo_camera.close()
            except Exception as error:
                print(f"Ошибка закрытия ServoCamera: {error}")

        average_fps = (
            frame_number / total_processing_time
            if total_processing_time > 0
            else 0.0
        )
        print_final_report(
            vessels,
            frame_number,
            average_fps,
            writer_path,
        )
        print("Готово")


if __name__ == "__main__":
    main()