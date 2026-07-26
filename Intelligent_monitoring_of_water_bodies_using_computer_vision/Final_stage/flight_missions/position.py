from pioneer_sdk2 import Pioneer
import time

drone = Pioneer()

try:
    while True:
        pos = drone.get_optical_data()
        if pos is not None:
            x, y, z = pos
            print(f"x={x:.2f}  y={y:.2f}  z={z:.2f}")
        time.sleep(0.1)

except KeyboardInterrupt:
    print("Остановка")

finally:
    drone.close_connection()
