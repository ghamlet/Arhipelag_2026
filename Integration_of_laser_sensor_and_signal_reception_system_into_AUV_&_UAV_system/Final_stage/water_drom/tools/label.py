"""Ручная разметка нарезанных патчей — для дообучения на своём видео.

    python tools/label.py --raw data/raw --out data/labeled

Показывает патч крупно. Клавиши: 0-9 — цифра, `x` — не цифра (мусор),
пробел — пропустить, `u` — отменить последнее, `q` — выход (прогресс
сохраняется, можно продолжить позже).

Размеченное складывается в data/labeled/<класс>/, откуда его подхватывает
    python train_model.py --real-dir data/labeled
"""
import argparse
import os
import shutil
import sys

import cv2

CLASSES = [str(d) for d in range(10)] + ["junk"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--out", default="data/labeled")
    ap.add_argument("--zoom", type=int, default=12)
    a = ap.parse_args()

    for c in CLASSES:
        os.makedirs(os.path.join(a.out, c), exist_ok=True)

    done = set()
    for c in CLASSES:
        done.update(os.listdir(os.path.join(a.out, c)))

    files = sorted(f for f in os.listdir(a.raw)
                   if f.endswith(".png") and not f.startswith("_") and f not in done)
    if not files:
        sys.exit("нечего размечать: все патчи уже разложены по классам")
    print(f"осталось разметить: {len(files)}")

    history = []
    i = 0
    while i < len(files):
        f = files[i]
        im = cv2.imread(os.path.join(a.raw, f), cv2.IMREAD_GRAYSCALE)
        big = cv2.resize(im, None, fx=a.zoom, fy=a.zoom, interpolation=cv2.INTER_NEAREST)
        big = cv2.cvtColor(big, cv2.COLOR_GRAY2BGR)
        cv2.putText(big, f"{i+1}/{len(files)}  {f}", (6, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 220), 1, cv2.LINE_AA)
        cv2.imshow("label: 0-9 / x=junk / space=skip / u=undo / q=quit", big)
        k = cv2.waitKey(0) & 0xFF

        if k == ord("q"):
            break
        if k == ord("u") and history:
            prev_f, prev_c = history.pop()
            src = os.path.join(a.out, prev_c, prev_f)
            if os.path.exists(src):
                os.remove(src)
            i = max(0, i - 1)
            continue
        if k == ord(" "):
            i += 1
            continue
        cls = None
        if ord("0") <= k <= ord("9"):
            cls = chr(k)
        elif k == ord("x"):
            cls = "junk"
        if cls is not None:
            shutil.copy(os.path.join(a.raw, f), os.path.join(a.out, cls, f))
            history.append((f, cls))
            i += 1

    cv2.destroyAllWindows()
    total = sum(len(os.listdir(os.path.join(a.out, c))) for c in CLASSES)
    print(f"размечено всего: {total}")
    for c in CLASSES:
        n = len(os.listdir(os.path.join(a.out, c)))
        if n:
            print(f"   {c:>4}: {n}")


if __name__ == "__main__":
    main()
