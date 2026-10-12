# -*- coding: utf-8 -*-
"""
小さな幾何の計算 (Maya に依存しない)。点は (x, y, z) のタプル。

    fan_triangles(4)                 # [0, 1, 2, 0, 2, 3]  四角形を三角形 2 つに
    toward((0, 0, 0), (10, 0, 0), 0.1)   # (1.0, 0.0, 0.0)  目の方へ 10% 寄せる
"""

__all__ = ["fan_triangles", "toward", "midpoint", "distance"]


def fan_triangles(count):
    """count 角形を扇形に三角形へ分けたときの、角の番号の並び (3 つずつ)。

    凸の多角形ならこれで正しく塗れる。凹んだ n 角形は少しはみ出すが、強調の表示には十分。
    """
    indices = []
    for i in range(1, count - 1):
        indices.extend((0, i, i + 1))
    return indices


def toward(point, eye, ratio):
    """point を eye の方へ、2 点の距離の ratio だけ寄せた点。

    面に重ねて描くと、奥行きの比べ合いで面に負けてちらつく。描く点をカメラへ少し寄せると、
    いつも面より手前になる (寄せる量は距離に比例させるので、遠くでも近くでも効く)。
    """
    return tuple(p + (e - p) * ratio for p, e in zip(point, eye))


def midpoint(a, b):
    return tuple((x + y) * 0.5 for x, y in zip(a, b))


def distance(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5
