#!/usr/bin/env python
# -*- coding: utf-8 -*-

from user.library import DroneLibrary
import time


def main():
    # Initialize the drone library
    drone = DroneLibrary()

    # Start the drone (enable autonomous mode)
    drone.start(takecontrol=True)

    try:
        # 1. Set depth (e.g., 100 cm)
        print("\n[1] Setting depth to 100 cm...")
        drone.set_depth(100)
        time.sleep(2)  # Wait for command execution

        # 2. Set course (e.g., 45 degrees)
        print("\n[2] Setting course to 45 degrees...")
        drone.set_course(45)
        time.sleep(2)

        # 3. Adjust roll angle (e.g., -10 degrees)
        print("\n[3] Adjusting roll angle to -10 degrees...")
        drone.change_roll(-10)
        time.sleep(2)

        # 4. Set speed (e.g., 50%)
        print("\n[4] Setting speed to 50%...")
        drone.set_speed(50)
        time.sleep(2)

        # 5. Control headlights (turn on at 70%)
        print("\n[5] Turning headlights on at 70%...")
        drone.set_headlight(70)
        time.sleep(2)

        # 6. Turn off headlights
        print("\n[6] Turning headlights off...")
        drone.set_headlight(0)
        time.sleep(1)

        # 7. Take control (switch to drone control)
        print("\n[7] Taking control (drone control mode)...")
        drone.set_online_mode()  # or drone.set_control(0)
        time.sleep(2)

        # 8. Release control (switch back to joystick)
        print("\n[8] Releasing control (joystick mode)...")
        drone.set_offline_mode()  # or drone.set_control(1)
        time.sleep(1)

        # 9. Stop the drone
        print("\n[9] Stopping the drone...")
        drone.stop()

    except Exception as e:
        print(f"Error: {e}")
        drone.stop()
        raise


if __name__ == "__main__":
    main()
