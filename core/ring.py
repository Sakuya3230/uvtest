# -*- coding: utf-8 -*-
"""
輪切りの線 (Maya に依存しない。段階 19)。

    stroke = Stroke((x0, y0), (x1, y1))   # ドラッグした線 (画面のピクセル)
    t, distance = stroke.project(point)   # (線に投げた位置 0〜1, 線からの距離)

断面の計算は core/section.py。はじめは今あるループから選ぶ方法 (案 A: 線に沿うエッジを候補にし、
閉じたループの点数を比べる) だったが、遅く、一周のループが無いと見つからなかったので、断面に置き換えた。
"""
import math

__all__ = ["Stroke", "MIN_LENGTH"]

MIN_LENGTH = 8.0      # これより短い線では探さない (ピクセル)


class Stroke(object):
    """画面の線 (始点・終点。ピクセル)。"""

    def __init__(self, start, end):
        self.start = (float(start[0]), float(start[1]))
        self.end = (float(end[0]), float(end[1]))
        dx, dy = self.end[0] - self.start[0], self.end[1] - self.start[1]
        self.length = math.sqrt(dx * dx + dy * dy)
        self.direction = (dx / self.length, dy / self.length) if self.length > 0 else (0.0, 0.0)

    def key(self):
        return (self.start, self.end)

    def project(self, point):
        """(線に投げた位置 0〜1, 線からの距離)。"""
        if self.length <= 0:
            return 0.0, math.hypot(point[0] - self.start[0], point[1] - self.start[1])
        px, py = point[0] - self.start[0], point[1] - self.start[1]
        along = px * self.direction[0] + py * self.direction[1]
        across = abs(px * self.direction[1] - py * self.direction[0])
        return along / self.length, across
