from pioneer_sdk2 import Pioneer, Camera, ImageViewer
import time
import select
import sys
import cv2

ALTITUDE = 1.8

# hover_mode: "seconds" — по таймеру, "input" — ждём Enter
HOVER_MODE = "input"
HOVER_SECONDS = 15

waypoints = [
    (-2.9, 0.8),
    (-3.1, 0.8)
]

drone = Pioneer()
camera = Camera()
viewer = ImageViewer()

current_point_label = None


def hover(seconds=None, mode=None):
    if mode is None:
        mode = HOVER_MODE

    if mode == "input":
        print("Напиши 'yes' чтобы продолжить...")
        try:
            while True:
                show_camera()
                if select.select([sys.stdin], [], [], 0)[0]:
                    line = sys.stdin.readline().strip()
                    if line == "yes":
                        break
                time.sleep(0.1)
       
        except KeyboardInterrupt:
            print("Остановка, посадка")
            drone.land()

            
    else:
        t = seconds if seconds is not None else HOVER_SECONDS
        end_time = time.time() + t
        while time.time() < end_time:
            show_camera()
            time.sleep(0.1)


def show_camera():
    frame = camera.get_cv_frame(timeout=1.0)
    if frame is not None:
        if current_point_label:
            cv2.putText(frame, current_point_label, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        viewer.imshow("pioneer_camera", frame)


def wait_for_point():
    while not drone.point_reached():
        # show_camera()
        time.sleep(0.1)


try:
    drone.arm()
    time.sleep(3)
    drone.takeoff()
    time.sleep(3)

    drone.go_to_local_point(x=0, y=0, z=ALTITUDE, yaw=0, time=5)
    wait_for_point()

    for i, (x, y) in enumerate(waypoints):
        print(f"Летим в точку {i+1}/{len(waypoints)}: x={x}, y={y}, z={ALTITUDE}")
        drone.go_to_local_point(x=x, y=y, z=ALTITUDE, yaw=0, time=5)
        wait_for_point()
        current_point_label = f"Point {i+1}: x={x}, y={y}"
        print(f"Точка {i+1} достигнута!")

        hover()




    print("Возвращаемся домой")
    current_point_label = "Home"
    drone.go_to_local_point(x=0, y=0, z=ALTITUDE, yaw=0, time=5)
    wait_for_point()

    drone.land()

except KeyboardInterrupt:
    print("Остановка, посадка")
    drone.land()

except Exception as error:
    print("Ошибка:", error)
    drone.land()

finally:
    viewer.close()
    camera.stop()
    drone.close_connection()
