"""Генератор обучающей выборки.

Цифры рендерятся системными шрифтами Windows и прогоняются через ту же
деградацию, что видна на записи с дрона: перспектива грани, поворот, размытие,
шум, низкий контраст, обрывы штрихов. Затем бинаризуются и нормализуются
ровно так же, как в detector.normalize — чтобы обучение и работа совпадали.

Интернет не нужен: шрифты берутся из C:\\Windows\\Fonts.
"""
import os
import random

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .detector import JUNK_CLASS, NUM_CLASSES, PATCH, normalize

FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
FONTS = ["arialbd.ttf", "arial.ttf", "ARIALNB.TTF", "calibrib.ttf", "verdanab.ttf",
         "tahomabd.ttf", "segoeuib.ttf", "seguisb.ttf", "trebucbd.ttf", "framd.ttf",
         "consolab.ttf", "micross.ttf", "verdana.ttf", "tahoma.ttf", "segoeui.ttf"]

_font_cache = {}


def available_fonts():
    return [f for f in FONTS if os.path.exists(os.path.join(FONT_DIR, f))]


def _font(name, size):
    key = (name, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    return _font_cache[key]


def _largest_component(mask):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n < 2:
        return None
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, _ = stats[i]
    if w < 2 or h < 3:
        return None
    return normalize(lab == i, x, y, w, h)


def render_glyph(digit, font_name, size=160):
    img = Image.new("L", (size * 2, size * 2), 0)
    ImageDraw.Draw(img).text((size, size), str(digit), fill=255,
                             font=_font(font_name, size), anchor="mm")
    a = np.array(img)
    ys, xs = np.nonzero(a)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def degrade(glyph, rng):
    """Один случайный «снимок» глифа глазами камеры дрона."""
    g = glyph.astype(np.float32)
    pad = int(max(g.shape) * 0.5)
    g = cv2.copyMakeBorder(g, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    H, W = g.shape

    # наклон грани кубика
    k = rng.uniform(0.0, 0.22)
    src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    dst = src + np.float32([[rng.uniform(-k, k) * W, rng.uniform(-k, k) * H]
                            for _ in range(4)])
    g = cv2.warpPerspective(g, cv2.getPerspectiveTransform(src, dst), (W, H))

    # поворот в плоскости грани
    M = cv2.getRotationMatrix2D((W / 2, H / 2), rng.uniform(-38, 38), 1.0)
    g = cv2.warpAffine(g, M, (W, H))

    # толщина штриха
    r = rng.random()
    if r < 0.30:
        g = cv2.dilate(g, np.ones((3, 3), np.uint8))
    elif r < 0.50:
        g = cv2.erode(g, np.ones((3, 3), np.uint8))

    ys, xs = np.nonzero(g > 40)
    if len(ys) == 0:
        return None
    g = g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

    # реальный размер цифры на кадре 320x240
    target_h = rng.randint(8, 42)
    scale = target_h / g.shape[0]
    new_w = max(3, int(g.shape[1] * scale * rng.uniform(0.8, 1.25)))
    g = cv2.resize(g, (new_w, target_h), interpolation=cv2.INTER_AREA)
    g = cv2.copyMakeBorder(g, 6, 6, 6, 6, cv2.BORDER_CONSTANT, value=0)

    # контраст, размытие, смаз, шум
    lo, hi = rng.uniform(0, 60), rng.uniform(140, 255)
    g = lo + g / 255.0 * (hi - lo)
    if rng.random() < 0.75:
        ks = rng.choice([3, 3, 5])
        g = cv2.GaussianBlur(g, (ks, ks), rng.uniform(0.5, 1.6))
    if rng.random() < 0.40:
        L = rng.randint(2, 5)
        ker = np.zeros((L, L), np.float32)
        if rng.random() < 0.5:
            ker[L // 2, :] = 1
        else:
            ker[:, L // 2] = 1
        g = cv2.filter2D(g, -1, ker / ker.sum())
    g = np.clip(g + np.random.normal(0, rng.uniform(2, 14), g.shape), 0, 255).astype(np.uint8)

    _, m = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))

    # Крупные цифры детектор отдаёт не залитыми, а контуром: black-hat
    # откликается на штрих толще своего ядра только по краям. Обучаем и на
    # таком виде, иначе большие цифры вблизи модель не узнаёт.
    if rng.random() < 0.30:
        m = cv2.morphologyEx(m, cv2.MORPH_GRADIENT,
                             np.ones((rng.choice([2, 3, 3]),) * 2, np.uint8))

    # частичное перекрытие / разрыв штриха
    if rng.random() < 0.25:
        h, w = m.shape
        cv2.circle(m, (rng.randint(0, w - 1), rng.randint(0, h - 1)),
                   rng.randint(2, max(3, h // 5)), 0, -1)
    return _largest_component(m)


def junk(rng):
    """Отрицательные примеры: рёбра кубика, блики, тени, обломки штрихов."""
    s = 60
    m = np.zeros((s, s), np.uint8)
    kind = rng.randint(0, 4)
    if kind == 0:
        cv2.line(m, (rng.randint(0, s), rng.randint(0, s)),
                 (rng.randint(0, s), rng.randint(0, s)), 255, rng.randint(2, 7))
    elif kind == 1:
        cv2.ellipse(m, (s // 2, s // 2), (rng.randint(6, 25), rng.randint(6, 25)),
                    rng.randint(0, 180), 0, 360, 255, -1)
    elif kind == 2:
        pts = np.array([[rng.randint(5, s - 5), rng.randint(5, s - 5)]
                        for _ in range(rng.randint(3, 6))])
        cv2.fillPoly(m, [pts], 255)
    elif kind == 3:
        x, y = rng.randint(0, s // 2), rng.randint(0, s // 2)
        cv2.rectangle(m, (x, y), (x + rng.randint(8, 30), y + rng.randint(8, 30)), 255, -1)
    else:
        cv2.ellipse(m, (s // 2, s // 2), (rng.randint(8, 22), rng.randint(8, 22)),
                    rng.randint(0, 180), 0, rng.randint(60, 200), 255, rng.randint(2, 6))
    if rng.random() < 0.5:
        m = ((cv2.GaussianBlur(m, (5, 5), 1.2)) > 100).astype(np.uint8) * 255
    return _largest_component(m)


def build(per_class=3000, seed=7, with_junk=True):
    """-> X (n,28,28) uint8, y (n,) int32; класс 10 = не цифра."""
    rng = random.Random(seed)
    np.random.seed(seed)
    fonts = available_fonts()
    if not fonts:
        raise RuntimeError(f"не найдено ни одного шрифта в {FONT_DIR}")

    X, y = [], []
    for d in range(10):
        got = 0
        while got < per_class:
            im = degrade(render_glyph(d, rng.choice(fonts)), rng)
            if im is not None:
                X.append(im); y.append(d); got += 1
    if with_junk:
        got = 0
        while got < per_class:
            im = junk(rng)
            if im is not None:
                X.append(im); y.append(JUNK_CLASS); got += 1
    return np.array(X, np.uint8), np.array(y, np.int32)
