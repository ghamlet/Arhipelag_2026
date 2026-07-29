from user.library import DroneLibrary
import time


def square_movement_after_diving(drone, time_to_move, speed):
    dive(drone)
    for _ in range(4):  # Проходим по каждой стороне квадрата
        move_forward(drone, time_to_move, speed)
        stop_movement(drone)
        turn_right(drone, 90)

    rise(drone)


def dive(drone):
    drone.set_depth(20)
    time.sleep(3)


def rise(drone):
    drone.set_depth(0)
    time.sleep(1)


def move_forward(drone, time_to_move, speed):
    drone.set_speed(speed)
    time.sleep(time_to_move)


def stop_movement(drone):
    drone.set_speed(0)


def turn_right(drone, angle):
    drone.change_course(angle)
    time.sleep(2)


if __name__ == "__main__":
    time_to_move = 5
    speed = 50

    drone = DroneLibrary()
    drone.start()

    square_movement_after_diving(drone, time_to_move, speed)

    drone.stop()
