#!/usr/bin/env python3
"""
Stabilization Script: Full Stabilization (Полная стабилизация)
Удерживает все параметры: глубина, тангаж, крен, курс одновременно.
Глубина задается в метрах (API принимает см), углы в градусах.
"""

import time
from user.library import DroneLibrary


def main():
    TARGET_DEPTH_M = 0.5       # метры
    TARGET_PITCH = 0           # градусы
    TARGET_ROLL = 0            # градусы
    TARGET_COURSE = 90         # градусы

    HOLD_TIME = 60             # секунд
    DEPTH_TOL_M = 0.3          # м
    ANGLE_TOL = 2.0            # градусы

    # API работает в сантиметрах
    TARGET_DEPTH_CM = int(TARGET_DEPTH_M * 100)
    DEPTH_TOL_CM = int(DEPTH_TOL_M * 100)

    drone = DroneLibrary()
    drone.start(takecontrol=True)

    print("[FullStabilize] Полная стабилизация дрона")
    print(f"  Глубина: {TARGET_DEPTH_M} м ({TARGET_DEPTH_CM} см) (±{DEPTH_TOL_M} м)")
    print(f"  Тангаж:  {TARGET_PITCH}° (±{ANGLE_TOL}°)")
    print(f"  Крен:    {TARGET_ROLL}° (±{ANGLE_TOL}°)")
    print(f"  Курс:    {TARGET_COURSE}° (±{ANGLE_TOL}°)")
    print(f"  Время:   {HOLD_TIME}с")
    print("-" * 65)

    # Начальная установка всех параметров
    drone.set_depth(TARGET_DEPTH_CM)
    drone.set_pitch(TARGET_PITCH)
    drone.set_roll(TARGET_ROLL)
    drone.set_course(TARGET_COURSE)

    time.sleep(3)

    start_time = time.time()
    corrections = {'depth': 0, 'pitch': 0, 'roll': 0, 'course': 0}
    max_dev = {'depth_cm': 0.0, 'pitch': 0.0, 'roll': 0.0, 'course': 0.0}

    try:
        while (time.time() - start_time) < HOLD_TIME:
            elapsed = time.time() - start_time
            remaining = HOLD_TIME - elapsed

            depth_cm = drone.get_depth()
            depth_m = depth_cm / 100.0
            pitch = drone.get_pitch()
            roll = drone.get_roll()
            course = drone.get_course()

            depth_dev_cm = abs(depth_cm - TARGET_DEPTH_CM)
            depth_dev_m = depth_dev_cm / 100.0
            pitch_dev = abs(pitch - TARGET_PITCH)
            roll_dev = abs(roll - TARGET_ROLL)
            course_dev = abs(((course - TARGET_COURSE + 180) % 360) - 180)

            if depth_dev_cm > max_dev['depth_cm']:
                max_dev['depth_cm'] = depth_dev_cm
            for k, v in [('pitch', pitch_dev), ('roll', roll_dev), ('course', course_dev)]:
                if v > max_dev[k]:
                    max_dev[k] = v

            d_ok = depth_dev_cm <= DEPTH_TOL_CM
            p_ok = pitch_dev <= ANGLE_TOL
            r_ok = roll_dev <= ANGLE_TOL
            c_ok = course_dev <= ANGLE_TOL

            print(f"[FullStabilize] Д: {depth_cm:6.1f}см({depth_m:.2f}м){'✓' if d_ok else '✗'}  "
                  f"Т: {pitch:+5.1f}°{'✓' if p_ok else '✗'}  "
                  f"К: {roll:+5.1f}°{'✓' if r_ok else '✗'}  "
                  f"Кр: {course:3d}°{'✓' if c_ok else '✗'} | {remaining:.0f}с")

            # Автокоррекция
            if not d_ok:
                drone.set_depth(TARGET_DEPTH_CM)
                corrections['depth'] += 1
            if not p_ok:
                drone.set_pitch(TARGET_PITCH)
                corrections['pitch'] += 1
            if not r_ok:
                drone.set_roll(TARGET_ROLL)
                corrections['roll'] += 1
            if not c_ok:
                drone.set_course(TARGET_COURSE)
                corrections['course'] += 1

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[FullStabilize] Прервано пользователем")
    finally:
        drone.set_online_mode()
        drone.stop()
        print(f"[FullStabilize] Дрон остановлен.")
        print(f"  Коррекции: глубина={corrections['depth']} тангаж={corrections['pitch']} крен={corrections['roll']} курс={corrections['course']}")
        print(f"  Макс. отклонения: глубина={max_dev['depth_cm']:.1f}см({max_dev['depth_cm']/100:.2f}м) тангаж={max_dev['pitch']:.1f}° крен={max_dev['roll']:.1f}° курс={max_dev['course']:.1f}°")


if __name__ == "__main__":
    main()