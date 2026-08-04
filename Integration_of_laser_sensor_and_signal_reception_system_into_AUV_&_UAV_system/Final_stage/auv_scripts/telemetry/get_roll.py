#!/usr/bin/env python3
"""
Telemetry Script: Get Roll (Получение крена)
Читает и выводит текущий крен дрона (наклон вбок) в градусах.
"""

import time
from user.library import DroneLibrary


def main():
    READ_INTERVAL = 0.5   # секунды между чтениями
    DURATION = 30         # секунд работы (0 = бесконечно)

    drone = DroneLibrary()
    drone.start(takecontrol=False)

    print("[Telemetry] Чтение крена (наклон вбок)")
    print(f"[Telemetry] Интервал: {READ_INTERVAL}с")
    print(f"[Telemetry] Длительность: {DURATION if DURATION > 0 else 'бесконечно'}с")
    print("-" * 40)

    start_time = time.time()
    count = 0

    try:
        while True:
            if DURATION > 0 and (time.time() - start_time) >= DURATION:
                break

            roll = drone.get_roll()
            count += 1
            elapsed = time.time() - start_time

            direction = "вправо" if roll > 0 else "влево" if roll < 0 else "уровень"
            print(f"[Telemetry] Крен: {roll:+4d}° ({direction}) | отсчет: {count} | время: {elapsed:.1f}с")

            time.sleep(READ_INTERVAL)

    except KeyboardInterrupt:
        print("\n[Telemetry] Прервано пользователем")
    finally:
        drone.set_online_mode()
        drone.stop()
        print(f"[Telemetry] Остановлено. Всего отсчетов: {count}")


if __name__ == "__main__":
    main()