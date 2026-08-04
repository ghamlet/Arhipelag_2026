#!/usr/bin/env python3
"""
Stabilization Script: Level Horizon (Выравнивание по горизонту)
Устанавливает дрон строго горизонтально (тангаж=0, крен=0) и удерживает.
"""



# работает 

import time
from user.library import DroneLibrary


def main():
    STABILIZE_TIME = 20     # секунд удержания горизонта
    TOLERANCE = 1.0         # допуск в градусах
    CORRECTION_INTERVAL = 2 # проверка и коррекция каждые N секунд

    drone = DroneLibrary()
    drone.start(takecontrol=True)

    print("[Stabilize] Выравнивание дрона по горизонту...")
    print(f"[Stabilize] Допуск: ±{TOLERANCE}°")
    print(f"[Stabilize] Интервал коррекции: {CORRECTION_INTERVAL}с")
    print(f"[Stabilize] Общее время: {STABILIZE_TIME}с")
    print("-" * 50)

    # Начальная установка в горизонт
    drone.set_pitch(0)
    drone.set_roll(0)
    time.sleep(2)

    start_time = time.time()
    correction_count = 0

    try:
        while (time.time() - start_time) < STABILIZE_TIME:
            elapsed = time.time() - start_time
            remaining = STABILIZE_TIME - elapsed

            pitch = drone.get_pitch()
            roll = drone.get_roll()

            pitch_ok = abs(pitch) <= TOLERANCE
            roll_ok = abs(roll) <= TOLERANCE

            pitch_status = "✓" if pitch_ok else "✗"
            roll_status = "✓" if roll_ok else "✗"

            print(f"[Stabilize] Тангаж: {pitch:6.1f}° {pitch_status}  Крен: {roll:6.1f}° {roll_status} | осталось: {remaining:.0f}с")

            # Автокоррекция если ушли за допуск
            if not pitch_ok or not roll_ok:
                if not pitch_ok:
                    drone.set_pitch(0)
                if not roll_ok:
                    drone.set_roll(0)
                correction_count += 1
                print(f"[Stabilize] >>> КОРРЕКЦИЯ #{correction_count} <<<")

            else:
                print("Its okey")

            time.sleep(CORRECTION_INTERVAL)

    except KeyboardInterrupt:
        print("\n[Stabilize] Прервано пользователем")
    finally:
        drone.set_online_mode()
        drone.stop()
        print(f"[Stabilize] Дрон остановлен. Всего коррекций: {correction_count}")


if __name__ == "__main__":
    main()