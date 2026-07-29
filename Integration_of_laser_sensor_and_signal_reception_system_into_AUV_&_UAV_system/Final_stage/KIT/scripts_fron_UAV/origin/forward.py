#!/usr/bin/env python3

from user.library import DroneLibrary
import time

if __name__ == "__main__":
    speed = 50

    drone = DroneLibrary()
    drone.start(False)

    drone.set_course(drone.get_course())
    drone.set_depth(drone.get_depth())
    drone.set_offline_mode()

    drone.set_speed(0)
    for i in range(0, 10):
        drone.set_speed(speed)
        print(f'depth: {drone.get_depth()}')
        time.sleep(5)
        drone.set_speed(0)
        print(f'depth: {drone.get_depth()}')
        drone.change_course(180)
        time.sleep(3)

    drone.stop()
