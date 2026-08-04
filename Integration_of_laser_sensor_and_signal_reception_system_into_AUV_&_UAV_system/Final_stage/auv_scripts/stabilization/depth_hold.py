#!/usr/bin/env python3
"""
Stabilization Script: Depth Hold (Удержание глубины)
Удерживает заданную глубину с автоматической коррекцией. Цель в метрах, API в см.
"""

import time
from user.library import DroneLibrary


def main():
    TARGET_DEPTH_M = 0.5         # метры
    HOLD_TIME = 60              # секунд удержания
    TOLERANCE_M = 0.1           # допуск в метрах
    CORRECTION_INTERVAL = 1     # проверка каждую секунду

    TARGET_DEPTH_CM = int(TARGET_DEPTH_M * 100)
    TOLERANCE_CM = int(TOLERANCE_M * 100)

    drone = DroneLibrary()
    drone.start(takecontrol=True)

    print(f"[DepthHold] Удержание глубины: {TARGET_DEPTH_M} м ({TARGET_DEPTH_CM} см)")
    print(f"[DepthHold] Допуск: ±{TOLERANCE_M} м (±{TOLERANCE_CM} см)")
    print(f"[DepthHold] Время удержания: {HOLD_TIME}с")
    print("-" * 55)

    drone.set_depth(TARGET_DEPTH_CM)
    time.sleep(3)  # даем время на погружение

    start_time = time.time()
    correction_count = 0
    max_deviation_cm = 0.0

    try:
        while (time.time() - start_time) < HOLD_TIME:
            elapsed = time.time() - start_time
            remaining = HOLD_TIME - elapsed

            current_cm = drone.get_depth()
            current_m = current_cm / 100.0
            deviation_cm = abs(current_cm - TARGET_DEPTH_CM)
            deviation_m = deviation_cm / 100.0

            if deviation_cm > max_deviation_cm:
                max_deviation_cm = deviation_cm

            status = "✓" if deviation_cm <= TOLERANCE_CM else "✗"

            print(f"[DepthHold] Глубина: {current_cm:6.1f} см ({current_m:.2f} м) отклонение: {deviation_cm:5.1f} см ({deviation_m:.2f} м) {status} | осталось: {remaining:.0f}с")

            if deviation_cm > TOLERANCE_CM:
                drone.set_depth(TARGET_DEPTH_CM)
                correction_count += 1
                print(f"[DepthHold] >>> КОРРЕКЦИЯ ГЛУБИНЫ #{correction_count} <<<")

            time.sleep(CORRECTION_INTERVAL)

    except KeyboardInterrupt:
        print("\n[DepthHold] Прервано пользователем")
    finally:
        drone.set_online_mode()
        drone.stop()
        print(f"[DepthHold] Дрон остановлен.")
        print(f"[DepthHold] Макс. отклонение: {max_deviation_cm:.1f} см ({max_deviation_cm/100:.2f} м), Коррекций: {correction_count}")


if __name__ == "__main__":
    main()