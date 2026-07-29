#!/usr/bin/env python3

import time
from user.library import DroneLibrary

if __name__ == "__main__":
    drone = DroneLibrary()

    waypoints = [(10, 20) , (30, 40), (50, 60)]

    drone.start()
    for point in waypoints:
        depth, speed = point
        drone.set_course(90)
        time.sleep(5)
        drone.set_depth(depth)
        drone.set_speed(speed)
        time.sleep(5)

    drone.stop()