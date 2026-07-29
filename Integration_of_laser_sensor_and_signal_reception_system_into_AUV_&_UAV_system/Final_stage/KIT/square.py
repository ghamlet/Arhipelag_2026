from user.library import DroneLibrary
import math
import time

def square_movement_after_diving(drone, side_length, speed):
    dive(drone)
    for _ in range(4):  # Проходим по каждой стороне квадрата
        move_forward(drone, side_length, speed)
        stop_movement(drone)
        turn_right(drone, 90)

    rise(drone)

def dive(drone):
    drone.dive()
    time.sleep(1)


def rise(drone):
    drone.rise()
    time.sleep(1)


def move_forward(drone, distance, speed):
    time_to_move = distance / speed
    drone.move_forward()
    time.sleep(time_to_move)


def stop_movement(drone):
    drone.stop_movement()


def turn_right(drone, angle):
    drone.turn_right()
    time.sleep(1)


if __name__ == "__main__":
    side_length = 5
    speed = 0.5

    drone = DroneLibrary()

    drone.start()
    square_movement_after_diving(drone, side_length, speed)

    drone.stop()
