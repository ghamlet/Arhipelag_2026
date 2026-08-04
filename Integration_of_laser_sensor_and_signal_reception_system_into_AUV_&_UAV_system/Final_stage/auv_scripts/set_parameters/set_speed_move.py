#!/usr/bin/env python3
"""
Set Parameter Script: Set Speed and Move (Установка скорости и движение)
Устанавливает скорость 80% и плывет заданное количество секунд.
"""

import time
from user.library import DroneLibrary


def main():
    TARGET_SPEED = 80       # проценты (0-100, отрицательное = назад)
    MOVE_TIME = 20          # секунд движения

    drone = DroneLibrary()
    drone.start(takecontrol=True)

    direction = "вперед" if TARGET_SPEED > 0 else "назад"
    print(f"[SetParam] Установка скорости: {abs(TARGET_SPEED)}% ({direction})")
    print(f"[SetParam] Движение: {MOVE_TIME} секунд")
    print("-" * 40)

    drone.set_speed(TARGET_SPEED)

    try:
        for i in range(MOVE_TIME):
            print(f"[SetParam] Движение... {i+1}/{MOVE_TIME}с (скорость: {TARGET_SPEED}%)")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[SetParam] Прервано пользователем")
    finally:
        drone.set_speed(0)
        time.sleep(1)
        drone.set_online_mode()
        drone.stop()
        print("[SetParam] Дрон остановлен, моторы выключены")


if __name__ == "__main__":
    main()