"""Измерение точности на размеченных вручную кадрах.

    python tools/evaluate.py vid4.avi --gt data/ground_truth.json

Файл эталона — это просто {номер кадра: [цифры, видимые глазом]}:

    {"4560": [1, 2, 6, 8], "4520": [1, 5, 6, 8, 9]}

Считаются precision / recall / F1 по мультимножеству цифр на кадре: сколько
из видимых цифр названы верно и сколько названо лишнего.
"""
import argparse
import collections
import json
import os
import sys

import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cube_digits.classifier import DigitClassifier          # noqa: E402
from cube_digits.detector import Params, detect, keep_best_per_cube  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--gt", required=True)
    ap.add_argument("--model", default=None)
    ap.add_argument("--conf", type=float, default=0.0)
    ap.add_argument("--per-cube", type=int, default=3)
    ap.add_argument("--no-rot", action="store_true")
    a = ap.parse_args()

    gt = {int(k): v for k, v in json.load(open(a.gt, encoding="utf-8")).items()}
    kw = {"path": a.model} if a.model else {}
    clf = DigitClassifier(rotations=not a.no_rot, **kw)
    params = Params()

    cap = cv2.VideoCapture(a.source)
    if not cap.isOpened():
        sys.exit(f"не удалось открыть {a.source}")

    tp = fp = fn = 0
    for frame_idx in sorted(gt):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok:
            print(f"кадр {frame_idx} не прочитан, пропуск")
            continue
        dets = detect(frame, params)
        labels, confs = clf.predict([d.patch for d in dets])
        if a.per_cube:
            keep = keep_best_per_cube(dets, labels, confs, a.per_cube, a.conf)
            pred = [int(labels[i]) for i in keep]
        else:
            pred = [int(l) for l, c in zip(labels, confs)
                    if int(l) < 10 and c >= a.conf]

        truth = gt[frame_idx]
        hit = sum((collections.Counter(pred) & collections.Counter(truth)).values())
        tp += hit
        fp += len(pred) - hit
        fn += len(truth) - hit
        print(f"кадр {frame_idx}: эталон={sorted(truth)} "
              f"распознано={sorted(pred)} совпало={hit}/{len(truth)}")
    cap.release()

    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
    print(f"\nверно={tp} лишних={fp} пропущено={fn}")
    print(f"precision={prec:.3f}  recall={rec:.3f}  F1={f1:.3f}")


if __name__ == "__main__":
    main()
