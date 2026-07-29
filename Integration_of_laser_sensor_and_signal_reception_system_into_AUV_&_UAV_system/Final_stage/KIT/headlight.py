#!/usr/bin/env python3

from user.library import DroneLibrary
import time

if __name__ == "__main__":
    drone = DroneLibrary()
    drone.start()
    drone.set_headlight(1)
    time.sleep(1)
    drone.set_headlight(0)
    time.sleep(1)
    drone.stop()