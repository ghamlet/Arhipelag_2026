#!/usr/bin/env python3
"""
Telemetry Script: Get Depth (Получение глубины)
Читает и выводит текущую глубину дрона (датчик возвращает см, показываем и в метрах).
"""

import time
import rospy    # пофискил залипание программы

from user.library import DroneLibrary


def main():
    READ_INTERVAL = 0.5   # секунды между чтениями
    DURATION = 30         # секунд работы (0 = бесконечно)

    drone = DroneLibrary()
    drone.start(takecontrol=False)

    print("[Telemetry] Чтение глубины (датчик в см)")
    print(f"[Telemetry] Интервал: {READ_INTERVAL}с")
    print(f"[Telemetry] Длительность: {DURATION if DURATION > 0 else 'бесконечно'}с")
    print("-" * 50)

    start_time = time.time()
    count = 0


    try:
        while not rospy.is_shutdown():
            if DURATION > 0 and (time.time() - start_time) >= DURATION:
                break

            depth_cm = drone.get_depth()
            depth_m = depth_cm / 100.0
            count += 1
            elapsed = time.time() - start_time

            print(f"[Telemetry] Глубина: {depth_cm:6.1f} см  ({depth_m:.2f} м) | отсчет: {count} | время: {elapsed:.1f}с")

            time.sleep(READ_INTERVAL)

    except KeyboardInterrupt:
        print("\n[Telemetry] Прервано пользователем")
    finally:
        drone.set_online_mode()
        drone.stop()
        print(f"[Telemetry] Остановлено. Всего отсчетов: {count}")


if __name__ == "__main__":
    main()