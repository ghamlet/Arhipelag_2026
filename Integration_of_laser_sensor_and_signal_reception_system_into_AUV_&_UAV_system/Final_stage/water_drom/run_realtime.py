"""Распознавание цифр на кубиках в реальном времени. Полностью офлайн.

    python run_realtime.py                     # файл vid4.avi
    python run_realtime.py --source 0          # камера / карта захвата
    python run_realtime.py --source rtsp://... # видеопоток дрона
    python run_realtime.py --no-display        # только консоль (для борта)
    python run_realtime.py --save out.mp4      # записать разметку в файл

Клавиши в окне: q — выход, пробел — пауза, d — показать маски детектора.
"""
import argparse
import collections
import sys
import time

import cv2
import numpy as np

from cube_digits.classifier import DigitClassifier
from cube_digits.detector import (Params, dark_strokes, detect,
                                  keep_best_per_cube, yellow_faces)
from cube_digits.tracker import DigitTracker, Track

GREEN, YELLOW, RED, WHITE = (60, 220, 60), (0, 220, 220), (60, 60, 230), (255, 255, 255)


def open_source(src):
    cap = cv2.VideoCapture(int(src) if str(src).isdigit() else src)
    if not cap.isOpened():
        sys.exit(f"не удалось открыть источник: {src}")
    return cap


def draw(frame, tracks, fps, scale=3):
    vis = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    for t in tracks:
        x, y, w, h = [v * scale for v in t.box]
        val = t.value
        if t.stable:
            color, text = GREEN, f"{val}"
        elif val is not None:
            color, text = YELLOW, f"{val}?"
        else:
            color, text = RED, ""
        cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)
        if text:
            cv2.putText(vis, text, (x, max(18, y - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
            cv2.putText(vis, f"{t.score:.2f}", (x, y + h + 16),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)

    digits = [str(t.value) for t in sorted(tracks, key=lambda t: t.box[0]) if t.stable]
    bar = f"FPS {fps:5.1f}   digits: {' '.join(digits) if digits else '-'}"
    cv2.rectangle(vis, (0, 0), (vis.shape[1], 26), (0, 0, 0), -1)
    cv2.putText(vis, bar, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, WHITE, 1, cv2.LINE_AA)
    return vis


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="/home/arrma/PROGRAMMS/Arhipelag_2026/Integration_of_laser_sensor_and_signal_reception_system_into_AUV_&_UAV_system/Final_stage/water_drom/vid4.avi", help="файл, индекс камеры или URL потока")
    ap.add_argument("--model", default=None)
    ap.add_argument("--conf", type=float, default=0.30, help="минимальная уверенность голоса")
    # По умолчанию выключено: если отсеять мусор до трекера, трек лишится
    # голосов «не цифра», а именно они и топят ложные треки при голосовании.
    ap.add_argument("--per-cube", type=int, default=0,
                    help="сколько цифр максимум брать с одного кубика (0 — без ограничения)")
    ap.add_argument("--hits", type=int, default=Track.MIN_HITS,
                    help="сколько кадров подряд нужно, чтобы объявить цифру")
    ap.add_argument("--score", type=float, default=Track.MIN_SCORE,
                    help="минимальная доля голосов за победителя")
    ap.add_argument("--scale", type=int, default=3, help="увеличение окна просмотра")
    ap.add_argument("--no-display", action="store_true")
    ap.add_argument("--save", default=None, help="записать видео с разметкой")
    ap.add_argument("--loop", action="store_true", help="повторять файл по кругу")
    a = ap.parse_args()

    Track.MIN_HITS = a.hits
    Track.MIN_SCORE = a.score

    clf = DigitClassifier(a.model) if a.model else DigitClassifier()
    params = Params()
    tracker = DigitTracker(min_conf=a.conf)

    cap = open_source(a.source)
    writer = None
    times = collections.deque(maxlen=30)
    last_report = None
    frame_idx = 0
    paused = False
    show_debug = False

    print("запуск… (q — выход)")
    while True:
        if not paused:
            ok, frame = cap.read()
            if not ok:
                if a.loop and not str(a.source).isdigit():
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                break

            t0 = time.perf_counter()
            dets = detect(frame, params)
            labels, confs = clf.predict([d.patch for d in dets])
            if a.per_cube:
                # на кубике видно две-три грани, значит и цифр не больше трёх
                keep = keep_best_per_cube(dets, labels, confs, a.per_cube)
                dets = [dets[i] for i in keep]
                labels = [labels[i] for i in keep]
                confs = [confs[i] for i in keep]
            live = tracker.update(frame_idx, [d.box for d in dets], labels, confs)
            times.append(time.perf_counter() - t0)
            frame_idx += 1

            reading = tracker.current_reading()
            digits = tuple(v for _, v, _ in reading)
            if digits != last_report:
                ts = frame_idx / max(cap.get(cv2.CAP_PROP_FPS) or 20, 1)
                print(f"[{ts:7.2f}s] " +
                      (" ".join(f"{v}({s:.2f})" for _, v, s in reading) or "—"))
                last_report = digits

        fps = 1.0 / max(np.mean(times), 1e-6) if times else 0.0

        if a.save and writer is None:
            h, w = frame.shape[:2]
            writer = cv2.VideoWriter(a.save, cv2.VideoWriter_fourcc(*"mp4v"),
                                     cap.get(cv2.CAP_PROP_FPS) or 20,
                                     (w * a.scale, h * a.scale))
        vis = draw(frame, live, fps, a.scale) if (a.save or not a.no_display) else None
        if writer is not None:
            writer.write(vis)

        if not a.no_display:
            cv2.imshow("cube digits", vis)
            if show_debug:
                roi = yellow_faces(frame, params)
                st = dark_strokes(frame, roi, params)
                cv2.imshow("debug: yellow / strokes",
                           cv2.resize(np.hstack([roi, st]), None, fx=2, fy=2,
                                      interpolation=cv2.INTER_NEAREST))
            k = cv2.waitKey(1) & 0xFF
            if k == ord("q"):
                break
            if k == ord(" "):
                paused = not paused
            if k == ord("d"):
                show_debug = not show_debug
                if not show_debug:
                    cv2.destroyWindow("debug: yellow / strokes")

    cap.release()
    if writer is not None:
        writer.release()
        print(f"видео сохранено: {a.save}")
    cv2.destroyAllWindows()
    if times:
        print(f"обработано кадров: {frame_idx}, "
              f"средняя скорость: {1.0/np.mean(times):.1f} FPS "
              f"({np.mean(times)*1000:.1f} мс/кадр)")
    seen = tracker.seen_digits()
    if seen:
        print("всего увидено за прогон (цифра: число кубиков): " +
              ", ".join(f"{d}: {n}" for d, n in seen.items()))


if __name__ == "__main__":
    main()
