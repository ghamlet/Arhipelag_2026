#!/usr/bin/env python3
"""
Telemetry Script: Get Course (Получение курса/рыскания)
Читает и выводит текущий курс дрона в градусах.
"""

import time
from user.library import DroneLibrary


def main():
    READ_INTERVAL = 0.5   # секунды между чтениями
    DURATION = 30         # секунд работы (0 = бесконечно)

    drone = DroneLibrary()
    drone.start(takecontrol=False)  # только чтение телеметрии

    print("[Telemetry] Чтение курса (рыскание)")
    print(f"[Telemetry] Интервал: {READ_INTERVAL}с")
    print(f"[Telemetry] Длительность: {DURATION if DURATION > 0 else 'бесконечно'}с")
    print("-" * 40)

    start_time = time.time()
    count = 0

    try:
        while True:
            if DURATION > 0 and (time.time() - start_time) >= DURATION:
                break

            course = drone.get_course()
            count += 1
            elapsed = time.time() - start_time

            print(f"[Telemetry] Курс: {course:3d}° | отсчет: {count} | время: {elapsed:.1f}с")

            time.sleep(READ_INTERVAL)

    except KeyboardInterrupt:
        print("\n[Telemetry] Прервано пользователем")
    finally:
        drone.set_online_mode()
        drone.stop()
        print(f"[Telemetry] Остановлено. Всего отсчетов: {count}")


if __name__ == "__main__":
    main()