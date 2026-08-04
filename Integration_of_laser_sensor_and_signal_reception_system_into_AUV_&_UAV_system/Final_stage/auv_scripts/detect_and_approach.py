#!/usr/bin/env python3
import time
import os
import sys
import cv2
import numpy as np
from user.library import DroneLibrary

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "water_drom"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "laser"))
from cube_digits.detector import Params, detect, keep_best_per_cube
from cube_digits.classifier import DigitClassifier
from cube_digits.tracker import DigitTracker
from laser_tx import send_digit

TARGET_DEPTH_M = 0.2
TARGET_PITCH = 0
TARGET_ROLL = 0

SEARCH_SPEED = 30
APPROACH_SPEED = 20

STRAIGHT_DURATION = 5
TURN_STEP_DEG = 3
TURN_STEP_SLEEP = 0.05
INIT_COURSE_SAMPLES = 5
APPROACH_TIMEOUT = 3.0

DEPTH_TOL_M = 0.05
ANGLE_TOL = 3.0

CAMERA_INDEX = 0
FRAME_WIDTH = 320
FRAME_HEIGHT = 240

CUBE_CONFIRM_FRAMES = 5
CUBE_POSITION_TOL = 30
CENTER_THRESHOLD_X = 20
TURN_GAIN = 0.15
CLOSE_FACE_AREA = 8000

DIGIT_MIN_HITS = 8

TARGET_DEPTH_CM = int(TARGET_DEPTH_M * 100)
DEPTH_TOL_CM = int(DEPTH_TOL_M * 100)

STUCK_PITCH_HISTORY_SIZE = 20
STUCK_PITCH_RANGE_TOL = 0.5
STUCK_COURSE_TOL = 1.0
STUCK_BACKUP_TIME = 3
STUCK_TURN_ANGLE = 90

SAVE_DIR = "/usr/local/drone_ros/src/drone/scripts/examples/auv_scripts/detect"


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
    print("\n[RECOVER] Дрон застрял! Восстановление...")
    drone.set_speed(-20)
    print(f"[RECOVER] Назад {backup_duration} с...")
    time.sleep(backup_duration)
    drone.set_speed(0)
    time.sleep(0.5)
    print(f"[RECOVER] Влево на {turn_angle}°...")
    angle = 0
    step = 3
    while angle < turn_angle:
        drone.change_course(step)
        time.sleep(0.05)
        angle += step
    print("[RECOVER] Готово\n")


def get_cube_position(dets):
    if not dets:
        return None
    cubes = {}
    for d in dets:
        cubes.setdefault(d.cube, []).append(d)
    best = max(cubes.values(), key=lambda ds: ds[0].face_area)
    xs = [d.box[0] + d.box[2] / 2 for d in best]
    ys = [d.box[1] + d.box[3] / 2 for d in best]
    return int(np.mean(xs)), int(np.mean(ys)), best[0].face_area


def maintain_depth_pitch_roll(drone):
    depth_cm = drone.get_depth()
    if abs(depth_cm - TARGET_DEPTH_CM) > DEPTH_TOL_CM:
        drone.set_depth(TARGET_DEPTH_CM)
    pitch = drone.get_pitch()
    roll = drone.get_roll()
    if abs(pitch) > ANGLE_TOL:
        drone.set_pitch(TARGET_PITCH)
    if abs(roll) > ANGLE_TOL:
        drone.set_roll(TARGET_ROLL)


def save_frame(frame, dets, save_dir, prefix):
    ts = time.strftime("%Y%m%d_%H%M%S")
    vis = frame.copy()
    for d in dets:
        x, y, w, h = d.box
        cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 255, 255), 2)
    path = os.path.join(save_dir, f"{prefix}_{ts}.jpg")
    cv2.imwrite(path, vis)
    print(f"[SAVE] {path}")


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    drone = DroneLibrary()
    drone.start(takecontrol=True)

    course_samples = []
    print("[INIT] Замер курса...")
    for i in range(INIT_COURSE_SAMPLES):
        c = drone.get_course()
        course_samples.append(c)
        print(f"[INIT]  Замер {i+1}: {c}°")
        time.sleep(0.15)
    TARGET_COURSE = int(np.mean(course_samples))
    print(f"[INIT] Начальный курс (среднее): {TARGET_COURSE}°")

    print("[MAIN] Поиск и сближение с жёлтым кубиком")
    print(f"  Глубина: {TARGET_DEPTH_M} м, курс: {TARGET_COURSE}°")
    print(f"  Поиск: {STRAIGHT_DURATION}с прямо + 360° поворот (циклически до обнаружения)")
    print(f"  Камера: индекс {CAMERA_INDEX}")
    print("-" * 50)

    drone.set_depth(TARGET_DEPTH_CM)
    drone.set_pitch(TARGET_PITCH)
    drone.set_roll(TARGET_ROLL)
    drone.set_course(TARGET_COURSE)
    time.sleep(3)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[MAIN] Ошибка: камера {CAMERA_INDEX} не открыта")
        drone.stop()
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    det_params = Params()
    clf = DigitClassifier()
    tracker = DigitTracker(min_hits=DIGIT_MIN_HITS)

    state = "SEARCH"
    found_digit = None
    frame_idx = 0
    pitch_history = []
    stuck_events = 0
    saved_frames = 0

    cube_consecutive_hits = 0
    cube_prev_pos = None
    cube_found_pos = None

    try:
        # ===================== SEARCH =====================
        while state == "SEARCH":
            # --- прямой участок ---
            print("[SEARCH] Прямой участок (5 с)")
            drone.set_speed(SEARCH_SPEED)
            drone.set_course(TARGET_COURSE)
            straight_start = time.time()

            while state == "SEARCH" and time.time() - straight_start < STRAIGHT_DURATION:
                maintain_depth_pitch_roll(drone)
                drone.set_course(TARGET_COURSE)

                pitch = drone.get_pitch()
                pitch_history.append(pitch)
                if len(pitch_history) > STUCK_PITCH_HISTORY_SIZE:
                    pitch_history.pop(0)

                ok, frame = cap.read()
                if ok:
                    dets = detect(frame, det_params)
                    cube_pos = get_cube_position(dets)
                    if cube_pos is not None:
                        cx, cy, _ = cube_pos
                        if cube_prev_pos is not None:
                            dx = abs(cx - cube_prev_pos[0])
                            dy = abs(cy - cube_prev_pos[1])
                            if dx < CUBE_POSITION_TOL and dy < CUBE_POSITION_TOL:
                                cube_consecutive_hits += 1
                            else:
                                cube_consecutive_hits = max(0, cube_consecutive_hits - 1)
                        else:
                            cube_consecutive_hits = 1
                        cube_prev_pos = (cx, cy)

                        if cube_consecutive_hits >= CUBE_CONFIRM_FRAMES:
                            print(f"\n[MAIN] Куб найден! Позиция: ({cx}, {cy})")
                            cube_found_pos = (cx, cy)
                            save_frame(frame, dets, SAVE_DIR, "cube_found")
                            saved_frames += 1
                            state = "APPROACH"
                            break
                    else:
                        cube_consecutive_hits = 0
                        cube_prev_pos = None

                depth_cm = drone.get_depth()
                course = drone.get_course()
                elapsed = time.time() - straight_start
                print(f"[STRAIGHT] {elapsed:.0f}/{STRAIGHT_DURATION}c  "
                      f"Д:{depth_cm}см T:{pitch:+.0f}° "
                      f"Курс:{course}° куб:{cube_consecutive_hits}")

                stuck, reason = check_stuck(drone, pitch_history, None, 0,
                                            STUCK_COURSE_TOL, STUCK_PITCH_RANGE_TOL)
                if stuck:
                    print(f"\n[STUCK] Движение заблокировано: {reason}")
                    recover_from_stuck(drone, SEARCH_SPEED,
                                       STUCK_BACKUP_TIME, STUCK_TURN_ANGLE)
                    drone.set_course(TARGET_COURSE)
                    stuck_events += 1
                    pitch_history.clear()
                    straight_start = time.time()
                    print("[STRAIGHT] Таймер сброшен после восстановления\n")

                time.sleep(0.5)

            if state != "SEARCH":
                break

            # --- поворот 360° ---
            print("[SEARCH] Поворот 360°")
            drone.set_speed(0)
            remaining = 360
            turn_stuck_retries = 0

            while state == "SEARCH" and remaining > 0:
                step = min(TURN_STEP_DEG, remaining)
                course_before = drone.get_course()
                drone.change_course(step)
                time.sleep(TURN_STEP_SLEEP)

                maintain_depth_pitch_roll(drone)

                pitch = drone.get_pitch()
                pitch_history.append(pitch)
                if len(pitch_history) > STUCK_PITCH_HISTORY_SIZE:
                    pitch_history.pop(0)

                ok, frame = cap.read()
                if ok:
                    dets = detect(frame, det_params)
                    cube_pos = get_cube_position(dets)
                    if cube_pos is not None:
                        cx, cy, _ = cube_pos
                        if cube_prev_pos is not None:
                            dx = abs(cx - cube_prev_pos[0])
                            dy = abs(cy - cube_prev_pos[1])
                            if dx < CUBE_POSITION_TOL and dy < CUBE_POSITION_TOL:
                                cube_consecutive_hits += 1
                            else:
                                cube_consecutive_hits = max(0, cube_consecutive_hits - 1)
                        else:
                            cube_consecutive_hits = 1
                        cube_prev_pos = (cx, cy)

                        if cube_consecutive_hits >= CUBE_CONFIRM_FRAMES:
                            print(f"\n[MAIN] Куб найден во время поворота! ({cx}, {cy})")
                            cube_found_pos = (cx, cy)
                            save_frame(frame, dets, SAVE_DIR, "cube_found")
                            saved_frames += 1
                            state = "APPROACH"
                            break
                    else:
                        cube_consecutive_hits = 0
                        cube_prev_pos = None

                remaining -= step
                course = drone.get_course()
                progress = 360 - remaining
                print(f"[TURN] {progress:.0f}/360° курс:{course}° куб:{cube_consecutive_hits}")

                stuck, reason = check_stuck(drone, pitch_history,
                                            course_before, step,
                                            STUCK_COURSE_TOL, STUCK_PITCH_RANGE_TOL)
                if stuck:
                    print(f"\n[STUCK] Поворот заблокирован: {reason}")
                    recover_from_stuck(drone, SEARCH_SPEED,
                                       STUCK_BACKUP_TIME, STUCK_TURN_ANGLE)
                    drone.set_course(TARGET_COURSE)
                    stuck_events += 1
                    turn_stuck_retries += 1
                    if turn_stuck_retries >= 2:
                        print("[TURN] Слишком много застреваний, переход к след. циклу")
                        break
                    print("[TURN] Поворачиваю заново")
                    remaining = 360
                    cube_consecutive_hits = 0
                    cube_prev_pos = None
                    continue

            if state != "SEARCH":
                break

            drone.set_course(TARGET_COURSE)
            print(f"[SEARCH] Поворот завершён, курс {TARGET_COURSE}° восстановлен")
            cube_consecutive_hits = 0
            cube_prev_pos = None

        if state == "SEARCH":
            print("[MAIN] Кубик не найден (прервано)")

        # ===================== APPROACH =====================
        if state == "APPROACH":
            print("[APPROACH] Сближение с кубиком")
            drone.set_speed(APPROACH_SPEED)
            if cube_found_pos is not None:
                cx, cy = cube_found_pos
                offset_x = cx - FRAME_WIDTH / 2
                correction = offset_x * TURN_GAIN
                correction = max(-30, min(30, correction))
                drone.set_course(TARGET_COURSE + correction)
            approach_start = time.time()

            while state == "APPROACH":
                maintain_depth_pitch_roll(drone)

                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue

                dets = detect(frame, det_params)
                cube_pos = get_cube_position(dets)

                if cube_pos is not None:
                    cx, cy, face_area = cube_pos
                    offset_x = cx - FRAME_WIDTH / 2
                    correction = offset_x * TURN_GAIN
                    correction = max(-30, min(30, correction))
                    drone.set_course(TARGET_COURSE + correction)

                    print(f"[APPROACH] ({cx},{cy}) площадь={face_area} "
                          f"смещ={offset_x:+.0f}px коррекция={correction:+.1f}°")

                    if face_area >= CLOSE_FACE_AREA:
                        print("[APPROACH] Кубик близко, чтение цифры")
                        state = "READ"
                        break

                    patches = [d.patch for d in dets]
                    labels, confs = clf.predict(patches)
                    keep = keep_best_per_cube(dets, labels, confs, min_conf=0.0)
                    keep_list = list(keep)
                    if keep_list:
                        dets_f = [dets[i] for i in keep_list]
                        boxes = [d.box for d in dets_f]
                        labels_f = labels[keep_list]
                        confs_f = confs[keep_list]
                        active = tracker.update(frame_idx, boxes, labels_f, confs_f)
                        frame_idx += 1
                        for t in active:
                            if t.stable and t.value is not None:
                                found_digit = t.value
                                print(f"\n{'='*50}")
                                print(f"[RESULT] ЦИФРА НАЙДЕНА: {found_digit}  "
                                      f"(score: {t.score:.2f})")
                                print(f"{'='*50}\n")
                                save_frame(frame, dets_f, SAVE_DIR,
                                           f"digit_{found_digit}")
                                saved_frames += 1
                                send_digit(drone, found_digit)
                                state = "DONE"
                                break
                    else:
                        frame_idx += 1

                elapsed = time.time() - approach_start
                if elapsed > APPROACH_TIMEOUT and state == "APPROACH":
                    print("[APPROACH] Таймаут сближения, чтение цифры")
                    state = "READ"
                    break

                stuck, reason = check_stuck(drone, pitch_history, None, 0,
                                            STUCK_COURSE_TOL, STUCK_PITCH_RANGE_TOL)
                if stuck:
                    print(f"\n[STUCK] Сближение заблокировано: {reason}")
                    recover_from_stuck(drone, APPROACH_SPEED,
                                       STUCK_BACKUP_TIME, STUCK_TURN_ANGLE)
                    drone.set_course(TARGET_COURSE)
                    stuck_events += 1
                    approach_start = time.time()
                    print("[APPROACH] Продолжаю после восстановления\n")

                time.sleep(0.1)

        # ===================== READ =====================
        if state == "READ":
            print("[READ] Чтение цифры")
            drone.set_speed(0)

            while state == "READ":
                maintain_depth_pitch_roll(drone)

                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue

                dets = detect(frame, det_params)
                if not dets:
                    time.sleep(0.1)
                    continue

                patches = [d.patch for d in dets]
                labels, confs = clf.predict(patches)
                keep = keep_best_per_cube(dets, labels, confs, min_conf=0.0)
                keep_list = list(keep)
                dets_f = [dets[i] for i in keep_list]
                boxes = [d.box for d in dets_f]
                labels_f = labels[keep_list]
                confs_f = confs[keep_list]

                active = tracker.update(frame_idx, boxes, labels_f, confs_f)
                frame_idx += 1

                for t in active:
                    if t.stable and t.value is not None:
                        found_digit = t.value
                        print(f"\n{'='*50}")
                        print(f"[RESULT] НАЙДЕНА ЦИФРА: {found_digit}  "
                              f"(score: {t.score:.2f}, hits: {t.hits})")
                        print(f"{'='*50}\n")
                        save_frame(frame, dets_f, SAVE_DIR, f"digit_{found_digit}")
                        saved_frames += 1
                        send_digit(drone, found_digit)
                        state = "DONE"
                        break

                if state != "DONE":
                    reading = tracker.current_reading(hold=4)
                    if reading:
                        print("[READ] Цифры: " +
                              " ".join(str(v) for _, v, _ in reading))
                    else:
                        print("[READ] Детекция...")
                    time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n[MAIN] Прервано пользователем")
    finally:
        drone.set_speed(0)
        drone.set_online_mode()
        drone.stop()
        cap.release()

        print(f"\n[MAIN] Дрон остановлен.")
        print(f"  Найденная цифра: {found_digit}")
        print(f"  Застреваний: {stuck_events}")
        print(f"  Сохранено кадров: {saved_frames}")
        if found_digit is not None:
            print(f"\n{'='*50}")
            print(f"  РЕЗУЛЬТАТ: ЦИФРА {found_digit}")
            print(f"{'='*50}")


if __name__ == "__main__":
    main()
