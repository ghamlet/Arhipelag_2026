"""Нарезка реальных цифр из видео — заготовка для разметки и дообучения.

    python tools/harvest.py vid4.avi --out data/raw --step 4

Кладёт нормализованные патчи 28x28 в data/raw/ и общий лист-контактку
data/raw/_sheet.png, чтобы глазами оценить, что вообще ловит детектор.
"""
import argparse
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cube_digits.detector import Params, detect  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--step", type=int, default=4, help="брать каждый N-й кадр")
    ap.add_argument("--limit", type=int, default=5000)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    cap = cv2.VideoCapture(int(a.source) if a.source.isdigit() else a.source)
    if not cap.isOpened():
        sys.exit(f"не удалось открыть {a.source}")

    p = Params()
    patches, idx = [], 0
    while len(patches) < a.limit:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % a.step == 0:
            for j, d in enumerate(detect(frame, p)):
                name = f"f{idx:06d}_{j}.png"
                cv2.imwrite(os.path.join(a.out, name), d.patch)
                patches.append(d.patch)
        idx += 1
    cap.release()
    print(f"кадров просмотрено: {idx}, вырезано цифр-кандидатов: {len(patches)}")

    if patches:
        cols, cell = 30, 32
        rows = (len(patches) + cols - 1) // cols
        sheet = np.full((rows * cell, cols * cell), 40, np.uint8)
        for k, im in enumerate(patches):
            r, c = divmod(k, cols)
            sheet[r * cell + 2:r * cell + 30, c * cell + 2:c * cell + 30] = im
        path = os.path.join(a.out, "_sheet.png")
        cv2.imwrite(path, cv2.resize(sheet, None, fx=2, fy=2,
                                     interpolation=cv2.INTER_NEAREST))
        print("контактка:", path)


if __name__ == "__main__":
    main()
