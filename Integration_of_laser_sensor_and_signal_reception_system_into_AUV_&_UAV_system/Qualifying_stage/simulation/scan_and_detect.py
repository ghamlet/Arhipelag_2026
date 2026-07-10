import cv2
import time
from pioneer_sdk import Pioneer, Camera

from drone_navigation import (
    CustomPioneer,
    ArucoDetector,
    ArucoMarkerAverager,
    FlightMissionRunner
)


flight_height = float(2)

FULL_MAP_COVERAGE_POINTS = [
    (-3, 3.5), (-3, -3.5), (0, -3.5), (0, 3.5), (3, 3.5), (3, -3.5)
]


if __name__ == "__main__":

    mission = FlightMissionRunner(FULL_MAP_COVERAGE_POINTS)
    aruco_detector = ArucoDetector(dictionary_type=cv2.aruco.DICT_4X4_100)
    marker_tracker_global_coord = ArucoMarkerAverager()
    marker_tracker_relative_coord = ArucoMarkerAverager()



    pioneer = Pioneer(
        name="pioneer", ip="127.0.0.1", mavlink_port=8000,
        connection_method="udpout", device="dev/serial0", baud=115200,
        logger=True, log_connection=True,simulator=True
    )

    print(f"Всего точек в маршруте: {mission.get_total_points()}")
    print("Маршрут:", mission.points)

    camera = Camera(ip="127.0.0.1", port=18000, log_connection=True, timeout=4)

    pioneer.arm()
    pioneer.takeoff()

    
    HOME_POINT = pioneer.get_local_position_lps(get_last_received=True)[:2]
    print(HOME_POINT)   # -2.74   2.77

    first_point = mission.get_next_point()
    x, y = first_point
    pioneer.go_to_local_point(x=x, y=y, z=flight_height, yaw=0)

    detect_count = 0
    marker_found = False

    # Цикл 1: пролёт по точкам, поиск маркера
    while not mission.is_complete():

        frame = camera.get_cv_frame()
        if frame is None:
            continue

        if aruco_detector.detect_markers_presence(frame, visual=True):
            detect_count += 1
            print(f"Детекция {detect_count}/5")

            if detect_count >= 5:
                marker_found = True
                break



        if pioneer.point_reached():
            next_point = mission.get_next_point()
            if next_point:
                x, y = next_point
                pioneer.go_to_local_point(x=x, y=y, z=flight_height, yaw=0)

        cv2.imshow("frame", frame)
        if cv2.waitKey(1) == ord('q'):
            cv2.destroyAllWindows()
            pioneer.land()
            pioneer.close_connection()
            del pioneer
            exit()

    # Маркер не найден — посадка
    if not marker_found:
        print("Маркер не найден, посадка")
        pioneer.land()
        pioneer.disarm()
        pioneer.close_connection()
        del pioneer
        exit()




    # Цикл 2: маркер найден — зависаем и собираем координаты
    print("Маркер найден! Зависание 5 сек...")
 
    pioneer.set_manual_speed(vx=0, vy=0, vz=0, yaw_rate=0)


    hover_start = time.time()
    while time.time() - hover_start < 5:
        frame = camera.get_cv_frame()
        if frame is None:
            continue

        if aruco_detector.detect_markers_presence(frame):
            markers_global_coord = aruco_detector.get_markers_global_positions(frame, pioneer)
            markers_relative_coord  = aruco_detector.get_markers_relative_positions(frame, pioneer,  verbose=False)


            if markers_global_coord:
                marker_tracker_global_coord.add_marker_sample(markers_global_coord)
            
            if markers_relative_coord:
                marker_tracker_relative_coord.add_marker_sample(markers_relative_coord)




    avg_global_coord = marker_tracker_global_coord.get_all_markers_coords()
    print("\n=== Усреднённые глобальные координаты маркеров ===")

    marker_id, coords = list(avg_global_coord.items())[0]
    print(f"  Маркер {marker_id}: ({coords[0]}, {coords[1]})")

    global_x = coords[0]
    global_y = coords[1]




    avg_relative_coord = marker_tracker_relative_coord.get_all_markers_coords()
    print("\n=== Усреднённые относительные координаты маркеров ===")
    
    marker_id, coords = list(avg_relative_coord.items())[0]
    print(f"  Маркер {marker_id}: x={coords[0]}m y={coords[1]}m z={coords[2]}m")



    pioneer.go_to_local_point(x=global_x, y=global_y, z=flight_height, yaw=0)
    while not pioneer.point_reached():
        continue

    print("прилетел над маркером")

    print("marker", marker_id)


    print("старт зависания на 5 секунд")
    hover_start = time.time()
    while time.time() - hover_start < 5:
        continue

    print("конец зависания")



    pioneer.go_to_local_point(x=HOME_POINT[0], y=HOME_POINT[1], z=flight_height, yaw=0)
    while not pioneer.point_reached():
        continue


    pioneer.land()
    pioneer.disarm()
    pioneer.close_connection()
    del pioneer
