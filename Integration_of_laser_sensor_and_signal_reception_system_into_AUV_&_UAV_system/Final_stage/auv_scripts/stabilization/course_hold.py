#!/usr/bin/env python3
"""
Stabilization Script: Course Hold (Удержание курса)
Удерживает заданный курс (рыскание) с автоматической коррекцией.
"""

import time
from user.library import DroneLibrary


def main():
    TARGET_COURSE = 45        # градусы (0-359)
    HOLD_TIME = 60            # секунд удержания
    TOLERANCE = 5.0           # допуск в градусах
    CORRECTION_INTERVAL = 1   # проверка каждую секунду

    drone = DroneLibrary()
    drone.start(takecontrol=True)

    print(f"[CourseHold] Удержание курса: {TARGET_COURSE}°")
    print(f"[CourseHold] Допуск: ±{TOLERANCE}°")
    print(f"[CourseHold] Время удержания: {HOLD_TIME}с")
    print("-" * 50)

    drone.set_course(TARGET_COURSE)
    time.sleep(2)

    start_time = time.time()
    correction_count = 0
    max_deviation = 0.0

    try:
        while (time.time() - start_time) < HOLD_TIME:
            elapsed = time.time() - start_time
            remaining = HOLD_TIME - elapsed

            current = drone.get_course()
            # Вычисляем кратчайшее отклонение с учетом перехода через 0/360
            diff = ((current - TARGET_COURSE + 180) % 360) - 180
            deviation = abs(diff)

            if deviation > max_deviation:
                max_deviation = deviation

            status = "✓" if deviation <= TOLERANCE else "✗"

            print(f"[CourseHold] Курс: {current:3d}° (цель: {TARGET_COURSE}°) отклонение: {diff:+6.1f}° {status} | осталось: {remaining:.0f}с")

            if deviation > TOLERANCE:
                drone.set_course(TARGET_COURSE)
                correction_count += 1
                print(f"[CourseHold] >>> КОРРЕКЦИЯ КУРСА #{correction_count} <<<")

            time.sleep(CORRECTION_INTERVAL)

    except KeyboardInterrupt:
        print("\n[CourseHold] Прервано пользователем")
    finally:
        drone.set_online_mode()
        drone.stop()
        print(f"[CourseHold] Дрон остановлен.")
        print(f"[CourseHold] Макс. отклонение: {max_deviation:.1f}°, Коррекций: {correction_count}")


if __name__ == "__main__":
    main()