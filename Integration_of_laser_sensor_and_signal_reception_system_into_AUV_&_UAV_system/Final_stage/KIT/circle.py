#!/usr/bin/env python3

from user.library import DroneLibrary
import math
import time


def circle_movement(drone, speed):
    angle = 0
    step = 2
    drone.set_speed(speed)
    while angle < 360:
        drone.change_course(step)
        time.sleep(0.5)
        angle = angle + step

    drone.set_speed(0)
    time.sleep(1)


if __name__ == "__main__":
    speed = 50

    drone = DroneLibrary()
    drone.start()
    circle_movement(drone, speed)

    drone.stop()