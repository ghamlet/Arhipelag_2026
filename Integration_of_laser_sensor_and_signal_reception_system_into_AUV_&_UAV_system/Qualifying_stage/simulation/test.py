from pioneer_sdk import Pioneer, Camera, VideoStream
import cv2
import math
import numpy as np
import time
import threading
import socket

from drone_navigation import (
    CustomPioneer,
    ArucoDetector,
    ArucoMarkerAverager,
    FlightMissionPathPlanner,
    FlightMissionRunner
)


flight_height = float(2)

FAST_MAP_POINTS = [
    (-1.7, 3.5), (-1.7, -3.5), (2.5, -3.5), (2.5, 2.5)
]



if __name__ == "__main__":

    hover_duration = 0

    mission = FlightMissionRunner(FAST_MAP_POINTS)
    aruco_detector = ArucoDetector(dictionary_type=cv2.aruco.DICT_4X4_100)
    marker_tracker = ArucoMarkerAverager()

 

    print(f"Всего точек в маршруте: {mission.get_total_points()}")
    print("Маршрут:", mission.points)

    pioneer = Pioneer(name="pioneer", ip="127.0.0.1", mavlink_port=8000, connection_method="udpout",
                      device="dev/serial0", baud=115200, logger=True, log_connection=True)


    camera = Camera(ip="127.0.0.1", port=18000, log_connection=True, timeout=4)



    pioneer.arm()
    pioneer.takeoff()

    first_point = mission.get_next_point()
    x, y = first_point
    
    # pioneer.go_to_local_point(x=x, y=y, z=flight_height, yaw=0)
    pioneer.go_to_local_point(x=0, y=0, z=flight_height, yaw=0)




    while not mission.is_complete():
        frame = camera.get_cv_frame()
        if frame is None:
            # time.sleep(0.05)
            continue



        if aruco_detector.detect_markers_presence(frame, visual=True):
            markers_global = aruco_detector.get_markers_global_positions(frame, pioneer)
            print(markers_global)
            # if markers_global:
            #     marker_tracker.add_marker_sample(markers_global)



        if pioneer.point_reached():
            next_point = mission.get_next_point()
            if next_point:
                x, y = next_point
                pioneer.go_to_local_point(x=x, y=y, z=flight_height, yaw=0)


        cv2.imshow("frame", frame)
        key = cv2.waitKey(1)
        if key == ord('q'):
            cv2.destroyAllWindows()
            pioneer.land()
            pioneer.close_connection()
            del pioneer
            break



    print(f"Миссия завершена! Пройдено: {mission.get_current_progress():.1f}%")

    pioneer.land()

    pioneer.disarm()
    pioneer.close_connection()
    del pioneer
