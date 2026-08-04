#!/usr/bin/env python3
"""
Set Parameter Script: Set Course (Установка курса)
Устанавливает заданный курс (рыскание) дрона в градусах.
"""

import time
from user.library import DroneLibrary


def main():
    TARGET_COURSE = 90      # градусы (0-359)
    HOLD_TIME = 15          # секунд удержания

    drone = DroneLibrary()
    drone.start(takecontrol=True)

    print(f"[SetParam] Установка курса: {TARGET_COURSE}°")
    print(f"[SetParam] Удержание: {HOLD_TIME} секунд")
    print("-" * 40)

    drone.set_course(TARGET_COURSE)

    try:
        for i in range(HOLD_TIME):
            current = drone.get_course()
            diff = ((current - TARGET_COURSE + 180) % 360) - 180
            print(f"[SetParam] Курс: {current:3d}° (цель: {TARGET_COURSE}°) отклонение: {diff:+.1f}° | {i+1}/{HOLD_TIME}с")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[SetParam] Прервано пользователем")
        drone.stop()

    finally:
        drone.set_online_mode()
        drone.stop()
        print("[SetParam] Дрон остановлен, моторы выключены")


if __name__ == "__main__":
    main()