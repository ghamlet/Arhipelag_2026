#!/usr/bin/env python3
"""
Детекция цифр на жёлтых кубиках с камеры.
Основано на water_drom/run_realtime.py.

Все настраиваемые параметры — в начале файла.
Запуск: python3 camera_detector.py
"""

import os
import sys
import time

import cv2
import numpy as np

# ─── Параметры (менять под свою камеру/воду) ────────────────────────
CAMERA_INDEX = "/home/arrma/PROGRAMMS/Arhipelag_2026/Integration_of_laser_sensor_and_signal_reception_system_into_AUV_&_UAV_system/Final_stage/water_drom/vid4.avi"
FRAME_WIDTH = 320
FRAME_HEIGHT = 240
PROCESS_FPS = 15

SHOW_GUI = True       

       # показывать окна imshow
FLAG_PATH = "/tmp/yellow_cube.flag"
STOP_PATH = "/tmp/yellow_cube.stop"

MARGIN_SEC = 1.0            # не выводить "Подплыви ближе" чаще чем раз в N сек
MIN_HITS = 4                # сколько кадров нужно для подтверждения цифры
MIN_SCORE = 0.70            # минимальная доля голосов за победителя
# ────────────────────────────────────────────────────────────────────

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "water_drom"))
from cube_digits.classifier import DigitClassifier  # noqa: E402
from cube_digits.detector import Params, detect, keep_best_per_cube  # noqa: E402
from cube_digits.tracker import DigitTracker, Track  # noqa: E402


def main():
    params = Params()
    clf = DigitClassifier()

    Track.MIN_HITS = MIN_HITS
    Track.MIN_SCORE = MIN_SCORE
    tracker = DigitTracker()

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[CAM] Ошибка: не удалось открыть камеру {CAMERA_INDEX}")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    interval = 1.0 / max(PROCESS_FPS, 1)
    last_report = None
    last_print = -MARGIN_SEC
    frame_idx = 0
    print("[CAM] Запуск детекции цифр. Для остановки: touch " + STOP_PATH)
    print(f"[CAM] Камера={CAMERA_INDEX}  SHOW_GUI={SHOW_GUI}")

    while True:
        if os.path.exists(STOP_PATH):
            print("[CAM] Получен сигнал остановки")
            break

        t0 = time.perf_counter()
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.1)
            continue

        dets = detect(frame, params)
        labels, confs = clf.predict([d.patch for d in dets])

        keep = keep_best_per_cube(dets, labels, confs, max_per_cube=3, min_conf=0.0)
        dets = [dets[i] for i in keep]
        labels = [labels[i] for i in keep]
        confs = [confs[i] for i in keep]

        live = tracker.update(frame_idx, [d.box for d in dets], labels, confs)
        frame_idx += 1

        now = time.time()

        # Ищем лучший трек (стабильный или нет)
        best = None
        for t in live:
            if t.value is None:
                continue
            if best is None or t.score > best.score:
                best = t

        # Если есть стабильный — берём только стабильные
        stable = [t for t in live if t.stable and t.value is not None]
        reading = tuple(v for t in stable for v in [t.value])

        if reading:
            if reading != last_report:
                line = " ".join(str(v) for v in reading)
                print(line)
                last_report = reading
                last_print = now
                _write_flag(now)
        elif best is not None and best.score >= MIN_SCORE * 0.8:
            if now - last_print >= MARGIN_SEC:
                print(f"{best.value}?")
                last_print = now
        else:
            if now - last_print >= MARGIN_SEC:
                print("Подплыви ближе")
                last_print = now

        if SHOW_GUI:
            vis = frame.copy()
            for t in live:
                x, y, w, h = t.box
                val = t.value
                if t.stable:
                    color = (60, 220, 60)
                    text = f"{val}"
                elif val is not None:
                    color = (0, 220, 220)
                    text = f"{val}?"
                else:
                    color = (60, 60, 230)
                    text = ""
                cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)
                if text:
                    cv2.putText(vis, text, (x, max(18, y - 6)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
                    cv2.putText(vis, f"{t.score:.2f}", (x, y + h + 16),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)

            digits_bar = " ".join(str(t.value) for t in live if t.stable)
            bar = f"digits: {digits_bar}" if digits_bar else "digits: —"
            cv2.rectangle(vis, (0, 0), (vis.shape[1], 24), (0, 0, 0), -1)
            cv2.putText(vis, bar, (8, 17), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (255, 255, 255), 1, cv2.LINE_AA)

            vis = cv2.resize(vis, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
            cv2.imshow("camera_detector", vis)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        elapsed = time.perf_counter() - t0
        time.sleep(max(0, interval - elapsed))

    cap.release()
    cv2.destroyAllWindows()
    _cleanup_flag()


def _write_flag(ts):
    try:
        with open(FLAG_PATH, "w") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)))
    except OSError:
        pass


def _cleanup_flag():
    try:
        if os.path.exists(FLAG_PATH):
            os.remove(FLAG_PATH)
    except OSError:
        pass


if __name__ == "__main__":
    main()
