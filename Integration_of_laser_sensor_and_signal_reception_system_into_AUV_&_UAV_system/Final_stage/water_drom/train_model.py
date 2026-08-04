"""Обучение локальной модели распознавания цифр. Интернет не нужен.

    python train_model.py                  # обучить и сохранить model/digit_mlp.xml
    python train_model.py --per-class 5000 # больше данных, дольше и точнее
    python train_model.py --real-dir data/labeled   # + свои размеченные патчи

Данные генерируются на лету из системных шрифтов (cube_digits/synth.py),
никакие датасеты скачивать не требуется. Размеченные вручную реальные патчи
(tools/harvest.py + tools/label.py) подмешиваются с повышенным весом.
"""
import argparse
import glob
import os
import time

import cv2
import numpy as np

from cube_digits import synth
from cube_digits.classifier import MODEL_PATH, features
from cube_digits.detector import JUNK_CLASS, NUM_CLASSES


def load_real(root):
    """data/labeled/<0..9|junk>/*.png -> (X, y)"""
    X, y = [], []
    for name in [str(d) for d in range(10)] + ["junk"]:
        cls = JUNK_CLASS if name == "junk" else int(name)
        for f in glob.glob(os.path.join(root, name, "*.png")):
            im = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
            if im is not None and im.shape == (28, 28):
                X.append(im); y.append(cls)
    if not X:
        return np.zeros((0, 28, 28), np.uint8), np.zeros(0, np.int32)
    return np.array(X, np.uint8), np.array(y, np.int32)


def train(per_class=3000, seed=7, hidden=160, iters=600, out=MODEL_PATH,
          real_dir=None, real_weight=8):
    t0 = time.time()
    print(f"шрифтов доступно: {len(synth.available_fonts())}")
    X, y = synth.build(per_class=per_class, seed=seed)
    print(f"выборка: {X.shape[0]} патчей, {NUM_CLASSES} классов "
          f"({time.time() - t0:.0f} с)")

    if real_dir:
        Xr, yr = load_real(real_dir)
        if len(Xr):
            # реальных примеров мало — повторяем их, чтобы они весили заметно
            X = np.concatenate([X] + [Xr] * real_weight)
            y = np.concatenate([y] + [yr] * real_weight)
            print(f"добавлено реальных: {len(Xr)} (вес x{real_weight}) -> всего {len(X)}")
        else:
            print(f"в {real_dir} размеченных патчей не найдено")

    F = features(X)
    print(f"признаков на патч: {F.shape[1]}")

    rng = np.random.RandomState(0)
    idx = rng.permutation(len(F))
    split = int(0.85 * len(F))
    tr, te = idx[:split], idx[split:]

    targets = np.full((len(F), NUM_CLASSES), -1.0, np.float32)
    targets[np.arange(len(F)), y] = 1.0

    mlp = cv2.ml.ANN_MLP_create()
    mlp.setLayerSizes(np.array([F.shape[1], hidden, NUM_CLASSES]))
    mlp.setActivationFunction(cv2.ml.ANN_MLP_SIGMOID_SYM, 1.0, 1.0)
    mlp.setTrainMethod(cv2.ml.ANN_MLP_BACKPROP, 0.0005, 0.1)
    mlp.setTermCriteria((cv2.TERM_CRITERIA_MAX_ITER + cv2.TERM_CRITERIA_EPS,
                         iters, 1e-5))

    t0 = time.time()
    mlp.train(F[tr], cv2.ml.ROW_SAMPLE, targets[tr])
    print(f"обучение: {time.time() - t0:.0f} с")

    pred = mlp.predict(F[te])[1].argmax(1)
    acc = (pred == y[te]).mean()
    print(f"точность на отложенной выборке: {acc:.4f}")
    for c in range(NUM_CLASSES):
        m = y[te] == c
        name = "не цифра" if c == JUNK_CLASS else str(c)
        if m.sum():
            print(f"   {name:>8}: {(pred[m] == c).mean():.3f}  (n={m.sum()})")

    os.makedirs(os.path.dirname(out), exist_ok=True)
    mlp.save(out)
    size_kb = os.path.getsize(out) / 1024
    print(f"модель сохранена: {out}  ({size_kb:.0f} КБ)")
    return acc


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-class", type=int, default=3000)
    ap.add_argument("--hidden", type=int, default=160)
    ap.add_argument("--iters", type=int, default=600)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=MODEL_PATH)
    ap.add_argument("--real-dir", default=None,
                    help="папка с размеченными патчами (tools/label.py)")
    ap.add_argument("--real-weight", type=int, default=8)
    a = ap.parse_args()
    train(a.per_class, a.seed, a.hidden, a.iters, a.out, a.real_dir, a.real_weight)
