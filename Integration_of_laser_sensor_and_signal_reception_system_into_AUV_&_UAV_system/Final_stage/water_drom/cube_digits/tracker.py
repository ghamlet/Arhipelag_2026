"""Сопровождение цифр между кадрами и голосование по времени.

Один кадр 320x240 из мутной воды — ненадёжный источник: смаз, блик, тень.
Но одна и та же цифра видна десятки кадров подряд. Трек копит взвешенные
по уверенности голоса, и итоговый ответ берётся по сумме голосов —
это и даёт устойчивый результат в реальном времени.
"""
from dataclasses import dataclass, field

import numpy as np

from .detector import JUNK_CLASS, NUM_CLASSES


@dataclass
class Track:
    tid: int
    box: tuple
    votes: np.ndarray = field(default_factory=lambda: np.zeros(NUM_CLASSES, np.float32))
    hits: int = 0
    misses: int = 0
    last_frame: int = 0

    @property
    def value(self):
        """Текущий ответ трека или None, пока цифра не набрала голосов."""
        digits = self.votes[:JUNK_CLASS]
        if digits.sum() <= 0:
            return None
        return int(digits.argmax())

    @property
    def score(self):
        """Доля голосов за победителя среди всех голосов, включая «не цифра»."""
        total = self.votes.sum()
        if total <= 0:
            return 0.0
        return float(self.votes[:JUNK_CLASS].max() / total)

    #: Сколько попаданий и какая доля голосов нужны, чтобы объявить ответ.
    #: Подобрано по эталонным кадрам vid4.avi: при 0.8 почти всё названное
    #: верно, при 0.6-0.7 находится больше цифр, но растёт число ложных.
    MIN_HITS = 8
    MIN_SCORE = 0.8

    @property
    def stable(self):
        return (self.hits >= self.MIN_HITS and self.value is not None
                and self.score >= self.MIN_SCORE)


def _center(b):
    x, y, w, h = b
    return np.array([x + w / 2.0, y + h / 2.0])


def _match_cost(a, b):
    """Расстояние между центрами, нормированное на размер — 1.0 = слишком далеко."""
    ca, cb = _center(a), _center(b)
    scale = max(a[2], a[3], b[2], b[3], 1)
    return float(np.linalg.norm(ca - cb) / (2.0 * scale))


class DigitTracker:
    def __init__(self, max_misses=8, max_cost=1.0, min_conf=0.30, min_hits=3):
        self.tracks = {}
        self.finished = []      # треки, ушедшие из кадра — журнал увиденного
        self.next_id = 1
        self.max_misses = max_misses
        self.max_cost = max_cost
        self.min_conf = min_conf
        self.min_hits = min_hits

    def update(self, frame_idx, boxes, labels, confs):
        """Привязать детекции кадра к трекам. -> список активных треков."""
        unmatched = set(range(len(boxes)))
        used = set()

        pairs = []
        for tid, tr in self.tracks.items():
            for i in unmatched:
                c = _match_cost(tr.box, boxes[i])
                if c < self.max_cost:
                    pairs.append((c, tid, i))
        pairs.sort()

        for c, tid, i in pairs:
            if tid in used or i not in unmatched:
                continue
            used.add(tid)
            unmatched.discard(i)
            tr = self.tracks[tid]
            tr.box = boxes[i]
            tr.hits += 1
            tr.misses = 0
            tr.last_frame = frame_idx
            if confs[i] >= self.min_conf:
                tr.votes[labels[i]] += float(confs[i])

        for i in sorted(unmatched):
            tid = self.next_id
            self.next_id += 1
            tr = Track(tid=tid, box=boxes[i], hits=1, last_frame=frame_idx)
            if confs[i] >= self.min_conf:
                tr.votes[labels[i]] += float(confs[i])
            self.tracks[tid] = tr

        for tid, tr in list(self.tracks.items()):
            if tid not in used and tr.last_frame != frame_idx:
                tr.misses += 1
                if tr.misses > self.max_misses:
                    if tr.stable:
                        self.finished.append(tr)
                    del self.tracks[tid]

        return [t for t in self.tracks.values() if t.last_frame == frame_idx]

    def current_reading(self, hold=4):
        """Стабильные цифры кадра слева направо — «то, что видит дрон сейчас».

        hold — сколько кадров держать ответ после пропажи детекции. Без этого
        показание мигает: цифра теряется на один-два кадра из-за смаза и тут
        же находится снова.
        """
        live = [t for t in self.tracks.values() if t.stable and t.misses <= hold]
        live.sort(key=lambda t: t.box[0])
        return [(t.tid, t.value, t.score) for t in live]

    def all_tracks(self):
        """Все устойчивые треки за прогон: и ушедшие, и ещё живые."""
        return self.finished + [t for t in self.tracks.values() if t.stable]

    def seen_digits(self):
        """Сводка за прогон: цифра -> сколько раз её видели как отдельный трек."""
        counts = {}
        for t in self.all_tracks():
            counts[t.value] = counts.get(t.value, 0) + 1
        return dict(sorted(counts.items()))
