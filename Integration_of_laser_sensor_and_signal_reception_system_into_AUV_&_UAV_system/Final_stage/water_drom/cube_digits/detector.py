"""Поиск цифр на жёлтых гранях кубиков.

Схема:
  1. HSV-маска жёлтого -> область интереса (грани кубика);
  2. black-hat по яркости внутри этой области -> тёмные штрихи (цифры);
  3. фильтрация связных компонент по геометрии;
  4. нормализация каждой цифры в бинарный патч 28x28 для классификатора.

Работает целиком на OpenCV, без сети и без GPU.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np

PATCH = 28          # размер нормализованного патча
_MARGIN = 4         # поле вокруг цифры внутри патча

JUNK_CLASS = 10     # отдельный класс «не цифра»: рёбра, блики, тени, обломки
NUM_CLASSES = 11    # цифры 0-9 плюс «не цифра»


@dataclass
class Params:
    """Пороги детектора. Меняются под другую воду/освещение без правки кода."""
    # HSV-диапазон жёлтого (H в шкале OpenCV 0..179)
    hsv_lo: tuple = (16, 60, 50)
    hsv_hi: tuple = (44, 255, 255)
    min_face_area: int = 500        # минимальная площадь жёлтого пятна, px
    close_ksize: int = 11           # закрытие маски: заклеить цифры внутри грани
    blackhat_ksize: int = 17        # ядро black-hat, чуть больше толщины штриха
    min_area: int = 15              # минимальная площадь цифры, px
    min_h: int = 6
    min_w: int = 3
    max_wh: int = 90
    ar_lo: float = 0.20             # ширина/высота
    ar_hi: float = 1.70
    fill_lo: float = 0.18           # площадь / площадь bbox
    fill_hi: float = 0.92
    max_area_frac: float = 0.12     # доля площади грани
    # Насколько глубоко цифра должна лежать внутри грани. На дальнем кубике
    # цифра занимает почти всю грань, поэтому отступ маленький, иначе такие
    # цифры отбраковываются целиком.
    erode_px: int = 2
    inside_frac: float = 0.55
    max_elong: float = 4.0          # отсев рёбер кубика (длинных тонких линий)
    min_thickness: float = 2.5


@dataclass
class Detection:
    box: tuple                       # (x, y, w, h) в координатах кадра
    patch: np.ndarray = field(repr=False)   # 28x28 uint8, бинарный
    area: int = 0
    face_area: int = 0
    cube: int = 0                    # номер жёлтого пятна (кубика), которому принадлежит


def yellow_faces(bgr, p: Params, labelled=False):
    """Маска жёлтых граней с залитыми дырами (цифры попадают внутрь области).

    labelled=True — дополнительно вернуть карту номеров пятен: каждое пятно
    это один кубик, а на кубике видно не больше двух-трёх граней.
    """
    hsv = cv2.cvtColor(cv2.GaussianBlur(bgr, (3, 3), 0), cv2.COLOR_BGR2HSV)
    raw = cv2.inRange(hsv, p.hsv_lo, p.hsv_hi)
    k = p.close_ksize
    m = cv2.morphologyEx(raw, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    roi = np.zeros_like(raw)
    ids = np.zeros(raw.shape, np.int32) if labelled else None
    n = 0
    for c in cnts:
        if cv2.contourArea(c) >= p.min_face_area:
            cv2.drawContours(roi, [c], -1, 255, -1)
            if labelled:
                n += 1
                cv2.drawContours(ids, [c], -1, n, -1)
    return (roi, ids) if labelled else roi


def dark_strokes(bgr, roi, p: Params):
    """Тёмные штрихи внутри жёлтой области.

    black-hat вытаскивает тёмные детали на светлом фоне и сам по себе убирает
    градиент освещения, поэтому одна и та же грань в тени и на свету
    обрабатывается одинаково.
    """
    gray = cv2.GaussianBlur(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), (3, 3), 0)
    k = p.blackhat_ksize
    bh = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    inside = bh[roi > 0]
    if inside.size < 300:
        return np.zeros_like(roi)
    t, _ = cv2.threshold(inside, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    t = max(float(t), 12.0)     # не ловить шум на однотонной грани без цифр
    m = ((bh >= t) & (roi > 0)).astype(np.uint8) * 255
    return cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))


def normalize(component, x, y, w, h):
    """Компонента -> бинарный патч 28x28 с сохранением пропорций."""
    sub = component[y:y + h, x:x + w].astype(np.uint8) * 255
    s = max(w, h)
    square = np.zeros((s, s), np.uint8)
    square[(s - h) // 2:(s - h) // 2 + h, (s - w) // 2:(s - w) // 2 + w] = sub
    inner = cv2.resize(square, (PATCH - 2 * _MARGIN, PATCH - 2 * _MARGIN),
                       interpolation=cv2.INTER_AREA)
    out = np.zeros((PATCH, PATCH), np.uint8)
    out[_MARGIN:PATCH - _MARGIN, _MARGIN:PATCH - _MARGIN] = inner
    return out


def detect(bgr, p: Params = None):
    """Список кандидатов-цифр в кадре."""
    p = p or Params()
    roi, cube_ids = yellow_faces(bgr, p, labelled=True)
    if not roi.any():
        return []
    strokes = dark_strokes(bgr, roi, p)
    e = 2 * p.erode_px + 1
    eroded = cv2.erode(roi, np.ones((e, e), np.uint8))
    face_area = int((roi > 0).sum())

    out = []
    n, lab, stats, _ = cv2.connectedComponentsWithStats(strokes, 8)
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if a < p.min_area or h < p.min_h or w < p.min_w:
            continue
        if h > p.max_wh or w > p.max_wh:
            continue
        ar = w / float(h)
        if not (p.ar_lo < ar < p.ar_hi):
            continue
        fill = a / float(w * h)
        if not (p.fill_lo < fill < p.fill_hi):
            continue
        if a > p.max_area_frac * face_area:
            continue
        comp = lab == i
        if (comp & (eroded > 0)).sum() / float(a) < p.inside_frac:
            continue
        ys, xs = np.nonzero(comp)
        rect = cv2.minAreaRect(np.stack([xs, ys], 1).astype(np.float32))
        side_a, side_b = rect[1]
        thin, thick = min(side_a, side_b), max(side_a, side_b)
        if thin < p.min_thickness or thick / max(thin, 1e-3) > p.max_elong:
            continue          # это ребро кубика, а не цифра
        out.append(Detection(box=(int(x), int(y), int(w), int(h)),
                             patch=normalize(comp, x, y, w, h),
                             area=int(a), face_area=face_area,
                             cube=int(np.bincount(cube_ids[comp]).argmax())))
    return out


def keep_best_per_cube(dets, labels, confs, max_per_cube=3, min_conf=0.0):
    """Оставить на каждом кубике только самые уверенные цифры.

    На кубике видно две-три грани, значит и цифр не больше трёх. Всё
    остальное, что прошло геометрию — блики, рёбра, тени, — отсекается
    этим ограничением, а не подбором очередного порога.
    """
    order = sorted(range(len(dets)), key=lambda i: -float(confs[i]))
    per_cube = {}
    keep = []
    for i in order:
        if int(labels[i]) >= JUNK_CLASS or confs[i] < min_conf:
            continue
        c = dets[i].cube
        if per_cube.get(c, 0) >= max_per_cube:
            continue
        per_cube[c] = per_cube.get(c, 0) + 1
        keep.append(i)
    return sorted(keep)
