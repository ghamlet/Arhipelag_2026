"""
Автономное поведение дрона: поиск ArUco-маркера, определение его координат,
точное позиционирование и возврат в точку взлёта.

Алгоритм:
  1. Дрон пролетает по заданным точкам и ищет маркер в камере.
  2. Когда маркер найден 5 раз подряд — он считается подтверждённым.
  3. Дрон зависает на 2 секунды, собирает координаты маркера и усредняет их.
  4. Летит точно над маркером, ждёт 5 секунд.
  5. Возвращается в домашнюю точку и садится.
"""

import cv2
import time
from pioneer_sdk import Pioneer, Camera


# ==================== FlightMissionRunner ====================

class FlightMissionRunner:
    """
    Простой раннер маршрута: на вход подаётся список точек (x, y),
    он по очереди выдаёт их через get_next_point().
    """

    def __init__(self, points):
        self.points = points
        self.current_index = 0
        self.is_complete_var = False

    def get_next_point(self):
        """Возвращает следующую точку маршрута или None, если всё пройдено."""
        if self.current_index < len(self.points):
            point = self.points[self.current_index]
            self.current_index += 1
            return point
        self.is_complete_var = True
        return None

    def get_total_points(self):
        """Сколько всего точек в маршруте."""
        return len(self.points)

    def is_complete(self):
        """True если все точки пройдены."""
        return self.is_complete_var


# ==================== ArucoDetector ====================

class ArucoDetector:
    """
    Ищет ArUco-маркеры на кадре и считает их координаты.

    Два основных метода:
      - get_markers_global_positions() — где маркер в мировых координатах
      - get_markers_relative_positions() — где маркер относительно дрона

    Система координат дрона (body-fixed):
      X — вправо (относительно носа)
      Y — вперёд (по направлению полёта)
      Z — вверх (в небо)
    """

    def __init__(self, dictionary_type=cv2.aruco.DICT_4X4_100):
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary_type)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.aruco_params.minMarkerPerimeterRate = 0.1
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        # размер изображения с камеры в пикселях
        self.image_size = (640, 480)
        # сколько метров земли покрывает кадр (ширина, высота)
        self.ground_cover = (4.4, 3.4)

    def detect_markers_presence(self, frame, visual=False):
        """
        Просто проверяет есть ли маркер на кадре.
        Если visual=True — рисует рамки вокруг маркеров.
        """
        corners, ids, _ = self.detector.detectMarkers(frame)
        if ids is not None:
            if visual:
                frame_copy = frame.copy()
                cv2.aruco.drawDetectedMarkers(frame_copy, corners, ids)
                cv2.imshow("DetectedMarkers", frame_copy)
                cv2.waitKey(1)
            return True
        elif visual:
            cv2.imshow("DetectedMarkers", frame)
            cv2.waitKey(1)
        return False

    def _get_scale(self):
        """Переводит пиксели в метры: сколько метров на один пиксель."""
        img_w, img_h = self.image_size
        gnd_w, gnd_h = self.ground_cover
        return gnd_w / img_w, gnd_h / img_h

    def _get_img_center(self):
        """Центр изображения в пикселях."""
        return self.image_size[0] / 2, self.image_size[1] / 2

    def get_markers_global_positions(self, frame, pioneer, verbose=False):
        """
        Считает глобальные координаты маркеров (где они лежат на карте).

        Логика: берём позицию дрона, прибавляем смещение маркера от центра кадра
        в метрах. Получаем мировые координаты маркера.

        Returns:
            dict: {marker_id: (global_x, global_y)} или None
        """
        corners, ids, _ = self.detector.detectMarkers(frame)
        if ids is None or len(ids) == 0:
            return None

        scale_x, scale_y = self._get_scale()
        img_cx, img_cy = self._get_img_center()
        drone_x, drone_y = pioneer.get_local_position_lps(get_last_received=True)[:2]

        global_markers = {}
        for i in range(len(ids)):
            marker_id = int(ids[i][0])
            # центр маркера в пикселях
            cx = int(corners[i][0][:, 0].mean())
            cy = int(corners[i][0][:, 1].mean())
            # смещение от центра кадра в метрах + позиция дрона = глобальные координаты
            global_x = drone_x + (cx - img_cx) * scale_x
            global_y = drone_y - (cy - img_cy) * scale_y
            global_markers[marker_id] = (round(global_x, 3), round(global_y, 3))

        if verbose:
            for mid, coords in global_markers.items():
                print(f"Маркер {mid}: {coords}")

        return global_markers

    def get_markers_relative_positions(self, frame, pioneer, verbose=False):
        """
        Считает координаты маркеров в системе координат дрона.

        X — вправо, Y — вперёд, Z — вверх.
        Маркер на земле будет иметь Z = -(высота дрона).

        Returns:
            dict: {marker_id: (rel_x, rel_y, rel_z)} или None
        """
        corners, ids, _ = self.detector.detectMarkers(frame)
        if ids is None or len(ids) == 0:
            return None

        scale_x, scale_y = self._get_scale()
        img_cx, img_cy = self._get_img_center()
        drone_z = pioneer.get_local_position_lps(get_last_received=True)[2]

        rel_markers = {}
        for i in range(len(ids)):
            marker_id = int(ids[i][0])
            cx = int(corners[i][0][:, 0].mean())
            cy = int(corners[i][0][:, 1].mean())

            # расстояние от центра кадра в пикселях
            dx_px = abs(cx - img_cx)
            dy_px = abs(cy - img_cy)
            # переводим в метры
            dx_m = dx_px * scale_x
            dy_m = dy_px * scale_y

            # знак зависит от того где маркер: справа/слева, выше/ниже центра
            if cx > img_cx:
                dx_m = -dx_m  # маркер правее центра — отрицательный X (влево от носа)
            if cy > img_cy:
                dy_m = dy_m   # маркер ниже центра — положительный Y (впереди)
            else:
                dy_m = -dy_m  # маркер выше центра — отрицательный Y (сзади)

            rel_markers[marker_id] = (round(dx_m, 3), round(dy_m, 3), round(-drone_z, 3))

        if verbose:
            for mid, coords in rel_markers.items():
                print(f"Маркер {mid}: x={coords[0]}m y={coords[1]}m z={coords[2]}m")

        return rel_markers


# ==================== ArucoMarkerAverager ====================

class ArucoMarkerAverager:
    """
    Собирает несколько измерений координат маркера и усредняет их.
    Нужен чтобы убрать шум — одно измерение неточное, а среднее по 10+ кадрам
    уже достаточно точное.
    """

    def __init__(self, min_samples=10, max_samples=100):
        self.marker_data = {}
        self.min_samples = min_samples  # минимум измерений для усреднения
        self.max_samples = max_samples  # максимум хранимых измерений

    def add_marker_sample(self, markers_dict):
        """Добавляет очередное измерение координат для каждого маркера."""
        if not markers_dict:
            return
        for marker_id, coords in markers_dict.items():
            if coords is None:
                continue
            if marker_id not in self.marker_data:
                self.marker_data[marker_id] = {'samples': [], 'avg_coords': None}
            samples = self.marker_data[marker_id]['samples']
            samples.append(coords)
            # если накопилось слишком много — убираем самое старое
            if len(samples) > self.max_samples:
                samples.pop(0)
            # как только набралось достаточно — считаем среднее
            if len(samples) >= self.min_samples:
                n_dims = len(samples[0])
                avg = tuple(
                    round(sum(s[d] for s in samples) / len(samples), 2)
                    for d in range(n_dims)
                )
                self.marker_data[marker_id]['avg_coords'] = avg

    def get_all_markers_coords(self):
        """Возвращает усреднённые координаты всех маркеров."""
        return {
            marker_id: tuple(round(c, 2) for c in data['avg_coords'])
            for marker_id, data in self.marker_data.items()
            if data['avg_coords'] is not None
        }


# ==================== Основной скрипт ====================

# высота полёта в метрах
flight_height = float(2)

# точки маршрута облёта территории
FULL_MAP_COVERAGE_POINTS = [
    (-3, 3.5), (-3, -3.5), (0, -3.5), (0, 3.5), (3, 3.5), (3, -3.5)
]


if __name__ == "__main__":

    # --- Инициализация ---
    mission = FlightMissionRunner(FULL_MAP_COVERAGE_POINTS)
    aruco_detector = ArucoDetector(dictionary_type=cv2.aruco.DICT_4X4_100)
    marker_tracker_global = ArucoMarkerAverager()
    marker_tracker_relative = ArucoMarkerAverager()

    pioneer = Pioneer(
        name="pioneer", ip="127.0.0.1", mavlink_port=8000,
        connection_method="udpout", device="dev/serial0", baud=115200,
        logger=False, log_connection=False, simulator=True
    )

    camera = Camera(ip="127.0.0.1", port=18000, log_connection=True, timeout=4)

    pioneer.arm()
    pioneer.takeoff()

    # запоминаем где взлетели чтобы потом вернуться
    HOME_POINT = pioneer.get_local_position_lps(get_last_received=True)[:2]

    first_point = mission.get_next_point()
    x, y = first_point
    pioneer.go_to_local_point(x=x, y=y, z=flight_height, yaw=0)

    detect_count = 0
    marker_found = False

    # --- Цикл 1: пролёт по точкам, поиск маркера ---
    # Летим по маршруту и смотрим в камеру.
    # Если маркер попал в кадр 5 раз подряд — значит не фантом, а настоящий.
    while not mission.is_complete():
        frame = camera.get_cv_frame()
        if frame is None:
            continue

        if aruco_detector.detect_markers_presence(frame):
            detect_count += 1
            if detect_count >= 5:
                marker_found = True
                break

        # когда долетели до текущей точки — берём следующую
        if pioneer.point_reached():
            next_point = mission.get_next_point()
            if next_point:
                x, y = next_point
                pioneer.go_to_local_point(x=x, y=y, z=flight_height, yaw=0)

        

    # если прошли весь маршрут и не нашли маркер — просто садимся
    if not marker_found:
        pioneer.land()
        pioneer.disarm()
        pioneer.close_connection()
        del pioneer
        exit()

    # --- Цикл 2: маркер найден, зависаем и собираем координаты ---
    # Останавливаем дрона и 2 секунды крутимся на месте,
    # собирая координаты маркера из каждого кадра.
    # Потом усредняем чтобы получить точное значение.
    pioneer.set_manual_speed(vx=0, vy=0, vz=0, yaw_rate=0)

    hover_start = time.time()
    while time.time() - hover_start < 2:
        frame = camera.get_cv_frame()
        if frame is None:
            continue
        if aruco_detector.detect_markers_presence(frame):
            mg = aruco_detector.get_markers_global_positions(frame, pioneer)
            mr = aruco_detector.get_markers_relative_positions(frame, pioneer)
            if mg:
                marker_tracker_global.add_marker_sample(mg)
            if mr:
                marker_tracker_relative.add_marker_sample(mr)

    # достаём усреднённые координаты
    avg_global = marker_tracker_global.get_all_markers_coords()
    marker_id, coords = list(avg_global.items())[0]
    global_x, global_y = coords[0], coords[1]

    # печатаем положение маркера относительно дрона
    avg_relative = marker_tracker_relative.get_all_markers_coords()
    print("\nПоложение маркера относительно собственной системы координат дрона")
    marker_id, coords = list(avg_relative.items())[0]
    print(f"x={coords[0]}m y={coords[1]}m z={coords[2]}m")

    # --- Точное позиционирование над маркером ---
    # Летим точно в глобальные координаты маркера на высоте полёта.
    # Если дрон не долетел за 5 секунд — выходим, чтобы не зависнуть.
    start_time = time.time()
    pioneer.go_to_local_point(x=global_x, y=global_y, z=flight_height, yaw=0)
    while not pioneer.point_reached():
        if time.time() - start_time > 5.0:
            break

    print(f"ID маркера {marker_id}")

    # зависаем над маркером на 5 секунд (по условию задачи)
    hover_start = time.time()
    while time.time() - hover_start < 5:
        continue

    # --- Возврат домой и посадка ---
    pioneer.go_to_local_point(x=HOME_POINT[0], y=HOME_POINT[1], z=flight_height, yaw=0)
    while not pioneer.point_reached():
        continue

    pioneer.land()
    pioneer.disarm()
    pioneer.close_connection()
    del pioneer
