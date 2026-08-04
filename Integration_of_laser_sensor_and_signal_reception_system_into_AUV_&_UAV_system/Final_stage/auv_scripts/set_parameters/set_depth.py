#!/usr/bin/env python3
"""
Set Parameter Script: Set Depth (Установка глубины)
Устанавливает заданную глубину дрона в метрах (API принимает см).
"""

import time
from user.library import DroneLibrary


def main():
    TARGET_DEPTH_M = 1      # метры (цель)
    HOLD_TIME = 20            # секунд удержания

    # API принимает сантиметры
    TARGET_DEPTH_CM = int(TARGET_DEPTH_M * 100)

    drone = DroneLibrary()
    drone.start(takecontrol=True)

    print(f"[SetParam] Установка глубины: {TARGET_DEPTH_M} м ({TARGET_DEPTH_CM} см)")
    print(f"[SetParam] Удержание: {HOLD_TIME} секунд")
    print("-" * 50)

    drone.set_depth(TARGET_DEPTH_CM)

    try:
        for i in range(HOLD_TIME):
            current_cm = drone.get_depth()
            current_m = current_cm / 100.0
            diff_m = current_m - TARGET_DEPTH_M
            print(f"[SetParam] Глубина: {current_cm:6.1f} см ({current_m:.2f} м) отклонение: {diff_m:+.2f} м | {i+1}/{HOLD_TIME}с")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[SetParam] Прервано пользователем")
    finally:
        drone.set_online_mode()
        drone.stop()
        print("[SetParam] Дрон остановлен, моторы выключены")


if __name__ == "__main__":
    main()