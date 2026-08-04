#!/usr/bin/env python3
"""
Set Parameter Script: Set Roll (Установка крен)
Устанавливает заданный угол крена дрона в градусах.
"""

import time
from user.library import DroneLibrary


def main():
    TARGET_ROLL = 0        # градусы (+ вправо, - влево)
    HOLD_TIME = 15          # секунд удержания

    drone = DroneLibrary()
    drone.start(takecontrol=True)

    direction = "вправо" if TARGET_ROLL > 0 else "влево" if TARGET_ROLL < 0 else "горизонт"
    print(f"[SetParam] Установка крен: {TARGET_ROLL}° ({direction})")
    print(f"[SetParam] Удержание: {HOLD_TIME} секунд")
    print("-" * 40)

    drone.set_roll(TARGET_ROLL)

    try:
        for i in range(HOLD_TIME):
            current = drone.get_roll()
            diff = current - TARGET_ROLL
            print(f"[SetParam] Крен: {current:5.1f}° (цель: {TARGET_ROLL}°) отклонение: {diff:+.1f}° | {i+1}/{HOLD_TIME}с")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[SetParam] Прервано пользователем")
    finally:
        drone.set_online_mode()
        drone.stop()
        print("[SetParam] Дрон остановлен, моторы выключены")


if __name__ == "__main__":
    main()