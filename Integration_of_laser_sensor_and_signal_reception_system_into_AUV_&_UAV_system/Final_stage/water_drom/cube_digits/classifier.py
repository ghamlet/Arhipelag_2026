"""Классификатор цифр: HOG + многослойный перцептрон из cv2.ml.

Модель обучается локально (train_model.py) и лежит рядом в model/digit_mlp.xml.
Вес модели — сотни килобайт, инференс на CPU: тысячи патчей в секунду,
так что на 320x240 это заведомо реальное время.
"""
import os

import cv2
import numpy as np

from .detector import JUNK_CLASS, PATCH

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "model", "digit_mlp.xml")

try:
    _hog_desc = cv2.HOGDescriptor((PATCH, PATCH), (14, 14), (7, 7), (7, 7), 9)
    _HOG_OK = True
except AttributeError:
    _HOG_OK = False


def _hog_compute(img):
    """Compute HOG features for a 28x28 image. Falls back to manual if cv2 lacks HOGDescriptor."""
    if _HOG_OK:
        return _hog_desc.compute(img).ravel()

    gx = cv2.Sobel(img, cv2.CV_32F, 1, 0, ksize=1)
    gy = cv2.Sobel(img, cv2.CV_32F, 0, 1, ksize=1)
    mag = np.sqrt(gx * gx + gy * gy)
    ang = np.arctan2(gy, gx) * 180.0 / np.pi
    ang[ang < 0] += 180.0

    cell = 7
    nbins = 9
    bw = 180.0 / nbins
    ncy, ncx = 28 // cell, 28 // cell  # 4, 4

    hist = np.zeros((ncy, ncx, nbins), np.float32)
    for cy in range(ncy):
        for cx in range(ncx):
            ys, xs = cy * cell, cx * cell
            block_mag = mag[ys:ys + cell, xs:xs + cell]
            block_ang = ang[ys:ys + cell, xs:xs + cell]
            for i in range(cell):
                for j in range(cell):
                    b = int(block_ang[i, j] / bw)
                    if b >= nbins:
                        b = nbins - 1
                    hist[cy, cx, b] += block_mag[i, j]

    feat = []
    for by in range(ncy - 1):
        for bx in range(ncx - 1):
            v = hist[by:by + 2, bx:bx + 2, :].ravel()
            n = np.sqrt(np.dot(v, v) + 1e-6)
            v = v / n
            v = np.clip(v, 0, 0.2)
            n = np.sqrt(np.dot(v, v) + 1e-6)
            v = v / n
            feat.append(v)
    return np.concatenate(feat)


def features(patches):
    """(n,28,28) uint8 -> (n,d) float32: HOG + огрублённые пиксели."""
    out = []
    for im in patches:
        h = _hog_compute(im)
        px = cv2.resize(im, (14, 14), interpolation=cv2.INTER_AREA).ravel() / 255.0
        out.append(np.concatenate([h, px.astype(np.float32) * 0.5]))
    return np.ascontiguousarray(np.array(out, np.float32))


def _softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z * 2.0)
    return e / e.sum(axis=1, keepdims=True)


class DigitClassifier:
    """Классификатор с перебором поворота на 0/90/180/270.

    Цифры напечатаны на разных гранях кубика, поэтому в кадре они лежат под
    произвольным кратным 90° углом (плюс наклон, который покрыт обучением).
    Поворот патча 28x28 на прямой угол выполняется точно, без интерполяции,
    так что перебор ничего не портит и стоит четырёх прогонов сети.
    """

    def __init__(self, path=MODEL_PATH, rotations=True, upright_bonus=0.03):
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"модель не найдена: {path}\nсначала запустите:  python train_model.py")
        self.model = cv2.ml.ANN_MLP_load(path)
        self.rotations = rotations
        # 6 и 9 — это один и тот же контур, повёрнутый на 180°, различить их
        # по картинке невозможно. Небольшая премия за меньший поворот делает
        # выбор предсказуемым: цифра, стоящая в кадре прямо, читается как есть.
        self.upright_bonus = upright_bonus

    def _probs(self, patches):
        _, raw = self.model.predict(features(patches))
        return _softmax(raw)

    def predict(self, patches, return_rotation=False):
        """-> (labels, confidences[, rotation_deg]). label == 10 = «не цифра»."""
        n = len(patches)
        if n == 0:
            empty = (np.zeros(0, np.int32), np.zeros(0, np.float32))
            return empty + ((np.zeros(0, np.int32),) if return_rotation else ())

        arr = np.asarray(patches)
        if not self.rotations:
            prob = self._probs(arr)
            lab = prob.argmax(1).astype(np.int32)
            conf = prob.max(1).astype(np.float32)
            return (lab, conf, np.zeros(n, np.int32)) if return_rotation else (lab, conf)

        # (4, n, 11): вероятности для каждого из четырёх поворотов
        probs = np.stack([self._probs(np.rot90(arr, k, axes=(1, 2)).copy())
                          for k in range(4)])
        turns = np.array([0, 1, 2, 1], np.float32)      # четвертей от «прямо»
        digit_score = probs[:, :, :JUNK_CLASS].max(2)   # (4, n)
        digit_score = digit_score - self.upright_bonus * turns[:, None]

        best_k = digit_score.argmax(0)                  # (n,)
        idx = np.arange(n)
        chosen = probs[best_k, idx]                     # (n, 11)
        lab = chosen.argmax(1).astype(np.int32)         # сюда может попасть и 10
        conf = chosen.max(1).astype(np.float32)
        if return_rotation:
            return lab, conf, (best_k * 90).astype(np.int32)
        return lab, conf


def is_digit(label):
    return 0 <= int(label) < JUNK_CLASS
