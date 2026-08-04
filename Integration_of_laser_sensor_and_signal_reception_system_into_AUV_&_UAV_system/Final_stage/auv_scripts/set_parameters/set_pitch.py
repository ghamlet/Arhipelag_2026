#!/usr/bin/env python3
"""
Set Parameter Script: Set Pitch (Установка тангажа)
Устанавливает заданный угол тангажа дрона в градусах.
"""

import time

from user.library import DroneLibrary


def main():
    TARGET_PITCH = 15       # градусы (+ вперед, - назад)
    HOLD_TIME = 15          # секунд удержания

    drone = DroneLibrary()
    drone.start(takecontrol=True)

    direction = "вперед" if TARGET_PITCH > 0 else "назад" if TARGET_PITCH < 0 else "горизонт"
    print(f"[SetParam] Установка тангажа: {TARGET_PITCH}° ({direction})")
    print(f"[SetParam] Удержание: {HOLD_TIME} секунд")
    print("-" * 40)

    drone.set_pitch(TARGET_PITCH)

    try:
        for i in range(HOLD_TIME):
            current = drone.get_pitch()
            diff = current - TARGET_PITCH
            print(f"[SetParam] Тангаж: {current:5.1f}° (цель: {TARGET_PITCH}°) отклонение: {diff:+.1f}° | {i+1}/{HOLD_TIME}с")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[SetParam] Прервано пользователем")
    finally:
        drone.set_online_mode()
        drone.stop()
        print("[SetParam] Дрон остановлен, моторы выключены")


if __name__ == "__main__":
    main()