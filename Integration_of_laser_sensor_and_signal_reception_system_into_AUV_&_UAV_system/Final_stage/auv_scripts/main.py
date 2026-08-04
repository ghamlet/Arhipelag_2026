#!/usr/bin/env python3
"""
Stabilization Script: Full Stabilization with Movement and 360° Turns
Удерживает глубину, тангаж, крен и курс, при этом дрон движется вперед,
выполняет повороты на 360° и продолжает движение.
"""

import time
import math
from user.library import DroneLibrary


def check_stuck(drone, pitch_history, last_course_before_turn, expected_turn,
                course_tol=1.0, pitch_range_tol=0.5, pitch_min_samples=10):
    cur_course = drone.get_course()

    if last_course_before_turn is not None and expected_turn > course_tol * 2:
        actual_change = abs(cur_course - last_course_before_turn)
        if actual_change > 180:
            actual_change = 360 - actual_change
        if actual_change < course_tol:
            return True, "course_blocked"

    if last_course_before_turn is None and len(pitch_history) >= pitch_min_samples:
        pitch_range = max(pitch_history) - min(pitch_history)
        if pitch_range < pitch_range_tol:
            return True, "pitch_too_stable"

    return False, None


def recover_from_stuck(drone, forward_speed, backup_duration=3, turn_angle=90):
    print("\n[RECOVER] Дрон застрял! Выполняю восстановление...")
    drone.set_speed(-20)
    print(f"[RECOVER] Отплываю назад (скорость: -20, {backup_duration} с)...")
    time.sleep(backup_duration)
    drone.set_speed(0)
    time.sleep(0.5)
    print(f"[RECOVER] Поворачиваю влево на {turn_angle}°...")
    angle = 0
    step = 3
    while angle < turn_angle:
        drone.change_course(step)
        time.sleep(0.05)
        angle += step
    drone.set_speed(forward_speed)
    time.sleep(1)
    print("[RECOVER] Восстановление завершено, продолжаю движение\n")


def perform_360_turn(drone, pitch_history,
                     turn_step, target_depth_cm, depth_tol_cm,
                     target_pitch, target_roll, angle_tol,
                     forward_speed, stuck_course_tol, stuck_pitch_range_tol,
                     stuck_backup_time, stuck_turn_angle):
    print("\n[FullStabilize] >>> НАЧАЛО ПОВОРОТА 360° <<<")
    drone.set_speed(0)
    time.sleep(1)

    angle_accumulated = 0
    while angle_accumulated < 360:
        course_before = drone.get_course()
        drone.change_course(turn_step)
        angle_accumulated += turn_step
        time.sleep(0.5)

        depth_cm = drone.get_depth()
        if abs(depth_cm - target_depth_cm) > depth_tol_cm:
            drone.set_depth(target_depth_cm)

        current_course = drone.get_course()
        print(f"[ПОВОРОТ] Угол: {current_course}°, пройдено: {angle_accumulated}°/360°")

        pitch = drone.get_pitch()
        roll = drone.get_roll()
        if abs(pitch) > angle_tol:
            drone.set_pitch(target_pitch)
        if abs(roll) > angle_tol:
            drone.set_roll(target_roll)

        stuck, reason = check_stuck(drone, pitch_history,
                                    course_before, turn_step,
                                    course_tol=stuck_course_tol,
                                    pitch_range_tol=stuck_pitch_range_tol)
        if stuck:
            print(f"\n[STUCK] Поворот заблокирован: {reason}")
            recover_from_stuck(drone, forward_speed, stuck_backup_time, stuck_turn_angle)
            print("[FullStabilize] >>> ПОВОРОТ 360° ПРЕРВАН <<<")
            return False

    print("[FullStabilize] >>> ПОВОРОТ 360° ЗАВЕРШЕН <<<")
    return True


def main():
    TARGET_DEPTH_M = 0.2
    TARGET_PITCH = 0
    TARGET_ROLL = 0

    FORWARD_SPEED = 50
    DISTANCE_BEFORE_TURN = 50
    TURN_STEP = 10

    DEPTH_TOL_M = 0.05
    ANGLE_TOL = 3.0
    COURSE_TOL = 3.0

    STUCK_PITCH_HISTORY_SIZE = 20
    STUCK_PITCH_RANGE_TOL = 0.5
    STUCK_COURSE_TOL = 1.0
    STUCK_BACKUP_TIME = 3
    STUCK_TURN_ANGLE = 90

    max_turns = 5

    TARGET_DEPTH_CM = int(TARGET_DEPTH_M * 100)
    DEPTH_TOL_CM = int(DEPTH_TOL_M * 100)

    drone = DroneLibrary()
    drone.start(takecontrol=True)

    TARGET_COURSE = drone.get_course()  # могу ли я сразу задать курс прямо?

    print("[FullStabilize] Полная стабилизация с движением и поворотами")
    print(f"  Глубина: {TARGET_DEPTH_M} м (±{DEPTH_TOL_M} м)")
    print(f"  Тангаж/Крен: ±{ANGLE_TOL}°")
    print(f"  Скорость: {FORWARD_SPEED}")
    print(f"  Дистанция до поворота: {DISTANCE_BEFORE_TURN} см")
    print(f"  Поворотов: {max_turns}  Застревание: курс<{STUCK_COURSE_TOL}° pitch<{STUCK_PITCH_RANGE_TOL}°")
    print("-" * 70)

    drone.set_depth(TARGET_DEPTH_CM)
    drone.set_pitch(TARGET_PITCH)
    drone.set_roll(TARGET_ROLL)
    drone.set_course(TARGET_COURSE)
    time.sleep(3)

    pitch_history = []
    stuck_events = 0
    turns_completed = 0
    corrections = {'depth': 0, 'pitch': 0, 'roll': 0, 'course': 0}
    max_dev = {'depth_cm': 0.0, 'pitch': 0.0, 'roll': 0.0, 'course': 0.0}

    try:
        while turns_completed < max_turns:
            # Фаза 1: разворот на 360°
            ok = perform_360_turn(
                drone, pitch_history,
                TURN_STEP, TARGET_DEPTH_CM, DEPTH_TOL_CM,
                TARGET_PITCH, TARGET_ROLL, ANGLE_TOL,
                FORWARD_SPEED, STUCK_COURSE_TOL, STUCK_PITCH_RANGE_TOL,
                STUCK_BACKUP_TIME, STUCK_TURN_ANGLE
            )
            if ok:
                turns_completed += 1
                print(f"[FullStabilize] Поворот #{turns_completed}/{max_turns} выполнен")
            else:
                stuck_events += 1

            # Фаза 2: движение вперёд
            drone.set_speed(FORWARD_SPEED)
            segment_start = time.time()
            pitch_history.clear()
            print(f"[FullStabilize] Движение вперёд, дистанция: {DISTANCE_BEFORE_TURN} см")

            while True:
                elapsed = time.time() - segment_start

                depth_cm = drone.get_depth()
                depth_m = depth_cm / 100.0
                pitch = drone.get_pitch()
                roll = drone.get_roll()
                course = drone.get_course()

                pitch_history.append(pitch)
                if len(pitch_history) > STUCK_PITCH_HISTORY_SIZE:
                    pitch_history.pop(0)

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
                c_ok = course_dev <= COURSE_TOL

                distance_traveled = elapsed * FORWARD_SPEED / 10.0

                print(f"[ДВИЖЕНИЕ] Д: {depth_cm:6.1f}см({depth_m:.2f}м){'✓' if d_ok else '✗'}  "
                      f"Т: {pitch:+5.1f}°{'✓' if p_ok else '✗'}  "
                      f"К: {roll:+5.1f}°{'✓' if r_ok else '✗'}  "
                      f"Кр: {course:3d}°{'✓' if c_ok else '✗'} | "
                      f"Дист: {distance_traveled:.0f}см/{DISTANCE_BEFORE_TURN}см | "
                      f"Поворотов: {turns_completed}/{max_turns}")

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

                stuck, reason = check_stuck(drone, pitch_history, None, 0,
                                            course_tol=STUCK_COURSE_TOL,
                                            pitch_range_tol=STUCK_PITCH_RANGE_TOL)
                if stuck:
                    print(f"\n[STUCK] Движение заблокировано: {reason}")
                    recover_from_stuck(drone, FORWARD_SPEED, STUCK_BACKUP_TIME, STUCK_TURN_ANGLE)
                    stuck_events += 1
                    segment_start = time.time()
                    pitch_history.clear()
                    time.sleep(1)
                    continue

                if distance_traveled >= DISTANCE_BEFORE_TURN:
                    print("[FullStabilize] Дистанция пройдена, готовлюсь к следующему повороту")
                    break

                time.sleep(1)

        print("\n[FullStabilize] Все повороты выполнены")

    except KeyboardInterrupt:
        print("\n[FullStabilize] Прервано пользователем")
    finally:
        drone.set_speed(0)
        drone.set_online_mode()
        drone.stop()

        print(f"\n[FullStabilize] Дрон остановлен.")
        print(f"  Поворотов 360° выполнено: {turns_completed}")
        print(f"  Коррекции: глубина={corrections['depth']} тангаж={corrections['pitch']} "
              f"крен={corrections['roll']} курс={corrections['course']}")
        print(f"  Макс. отклонения: глубина={max_dev['depth_cm']:.1f}см "
              f"тангаж={max_dev['pitch']:.1f}° крен={max_dev['roll']:.1f}° "
              f"курс={max_dev['course']:.1f}°")
        print(f"  Застреваний обнаружено: {stuck_events}")


if __name__ == "__main__":
    main()
