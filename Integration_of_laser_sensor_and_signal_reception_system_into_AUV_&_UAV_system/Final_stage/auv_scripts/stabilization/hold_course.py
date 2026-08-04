#!/usr/bin/env python3
"""
Stabilization Script: Hold Course (Удержание курса)
Удерживает заданный курс (рыскание) с заданной точностью.
"""

import time
from user.library import DroneLibrary


def main():
    TARGET_COURSE = 90      # градусы
    HOLD_TIME = 30          # секунд удержания
    TOLERANCE = 3.0         # допуск в градусах

    drone = DroneLibrary()
    drone.start(takecontrol=True)

    print(f"[Stabilize] Удержание курса: {TARGET_COURSE}°")
    print(f"[Stabilize] Допуск: ±{TOLERANCE}°")
    print(f"[Stabilize] Удержание: {HOLD_TIME} секунд")
    print("-" * 40)

    drone.set_course(TARGET_COURSE)

    try:
        for i in range(HOLD_TIME):
            current_course = drone.get_course()
            diff = ((current_course - TARGET_COURSE + 180) % 360) - 180
            diff_abs = abs(diff)

            course_ok = diff_abs <= TOLERANCE
            status = "✓" if course_ok else "✗"
            direction = "влево" if diff > 0 else "вправо" if diff < 0 else "норма"

            print(f"[Stabilize] Курс: {current_course:3d}° (цель: {TARGET_COURSE}°) отклонение: {diff:+.1f}° ({direction}) {status} | {i+1}/{HOLD_TIME}с")

            if not course_ok:
                drone.set_course(TARGET_COURSE)
            else:
                print("ok")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[Stabilize] Прервано пользователем")
    finally:
        drone.set_online_mode()
        drone.stop()
        print("[Stabilize] Дрон остановлен, моторы выключены")


if __name__ == "__main__":
    main()