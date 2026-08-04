#!/usr/bin/env python3
"""
Telemetry Script: Get Pitch (Получение тангажа)
Читает и выводит текущий тангаж дрона (наклон вперед/назад) в градусах.
"""

import time
from user.library import DroneLibrary


def main():
    READ_INTERVAL = 0.5   # секунды между чтениями
    DURATION = 30         # секунд работы (0 = бесконечно)

    drone = DroneLibrary()
    drone.start(takecontrol=False)

    print("[Telemetry] Чтение тангажа (наклон вперед/назад)")
    print(f"[Telemetry] Интервал: {READ_INTERVAL}с")
    print(f"[Telemetry] Длительность: {DURATION if DURATION > 0 else 'бесконечно'}с")
    print("-" * 40)

    start_time = time.time()
    count = 0

    try:
        while True:
            if DURATION > 0 and (time.time() - start_time) >= DURATION:
                break

            pitch = drone.get_pitch()
            count += 1
            elapsed = time.time() - start_time

            direction = "вперед" if pitch > 0 else "назад" if pitch < 0 else "уровень"
            print(f"[Telemetry] Тангаж: {pitch:+4d}° ({direction}) | отсчет: {count} | время: {elapsed:.1f}с")

            time.sleep(READ_INTERVAL)

    except KeyboardInterrupt:
        print("\n[Telemetry] Прервано пользователем")
    finally:
        drone.set_online_mode()
        drone.stop()
        print(f"[Telemetry] Остановлено. Всего отсчетов: {count}")


if __name__ == "__main__":
    main()