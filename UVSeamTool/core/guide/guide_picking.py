"""
画面の上の位置から、いちばん近いガイドを選ぶ (Maya に依存しない。画面の座標で計算する)。
"""

from __future__ import annotations

import math


def nearest_guide(screen_lines, position, max_distance):
    """position (x, y) にいちばん近いガイドの id。max_distance (ピクセル) より遠ければ None。

    screen_lines は [(ガイドの id, [(x, y), ...])]。ガイドの線を画面に写した点の列。
    """
    best_id       = None
    best_distance = max_distance
    for guide_id, points in screen_lines:
        for a, b in zip(points, points[1:]):
            distance = _distance_to_segment(position, a, b)
            if distance <= best_distance:
                best_id       = guide_id
                best_distance = distance

    return best_id


def nearest_point(screen_points, position, max_distance):
    """position にいちばん近い点の (ガイドの id, 点の番号)。max_distance より遠ければ None。

    screen_points は [(ガイドの id, 点の番号, (x, y))]。
    """
    best          = None
    best_distance = max_distance
    for guide_id, index, (x, y) in screen_points:
        distance = math.hypot(position[0] - x, position[1] - y)
        if distance <= best_distance:
            best          = (guide_id, index)
            best_distance = distance

    return best


def nearest_line_vertex(screen_segments, position, max_distance):
    """position にいちばん近い区間の上の頂点 (ガイドの id, 区間の番号, 頂点)。max_distance より遠ければ None。

    screen_segments は [(ガイドの id, 区間の番号, 頂点の列, 画面の点の列)]。いちばん近い線分を探し、
    その両端の頂点のうち position に近い方を返す (点を挿入する場所)。
    """
    best          = None
    best_distance = max_distance
    for guide_id, segment_index, vertices, pixels in screen_segments:
        for k in range(len(pixels) - 1):
            distance = _distance_to_segment(position, pixels[k], pixels[k + 1])
            if distance <= best_distance:
                nearer        = k if _length(position, pixels[k]) <= _length(position, pixels[k + 1]) else k + 1
                best          = (guide_id, segment_index, vertices[nearer])
                best_distance = distance

    return best


def distance_to_line(position, pixels):
    """position から画面の折れ線 pixels ((x, y) の列) までのいちばん近い距離 (線分が無ければ無限大)。"""
    return min((_distance_to_segment(position, a, b) for a, b in zip(pixels, pixels[1:])), default=float("inf"))


def guides_in_rect(screen_lines, rect):
    """矩形 (左, 下, 右, 上) に線が少しでもかかるガイドの id のリスト。screen_lines は nearest_guide と同じ形。"""
    return [guide_id for guide_id, points in screen_lines
            if any(_segment_touches_rect(a, b, rect) for a, b in zip(points, points[1:]))]


def points_in_rect(screen_points, rect):
    """矩形 (左, 下, 右, 上) の中の点の (ガイドの id, 点の番号) のリスト。screen_points は nearest_point と同じ形。"""
    return [(guide_id, index) for guide_id, index, pixel in screen_points if _inside(pixel, rect)]


def combine_selection(selected, item, shift, ctrl):
    """クリックしたもの (ガイドの id・点など) で、選択 (frozenset) を変える。修飾キーは Maya と同じ。

    なし = それだけを選ぶ / Shift = 切り替え / Ctrl = 外す / Ctrl+Shift = 足す。
    """
    return combine_selection_many(selected, [item], shift, ctrl)


def combine_selection_many(selected, items, shift, ctrl):
    """いくつかのもの (矩形で選んだガイドなど) で、選択を変える。修飾キーは combine_selection と同じ。"""
    items = frozenset(items)
    if shift and ctrl:
        return selected | items

    if ctrl:
        return selected - items

    if shift:
        return selected ^ items

    return items


def _segment_touches_rect(a, b, rect):
    # 線分 a-b が矩形にかかるか (端が中にあるか、矩形の辺と交わるか)
    left, bottom, right, top = rect
    if _inside(a, rect) or _inside(b, rect):
        return True

    corners = [(left, bottom), (right, bottom), (right, top), (left, top)]

    return any(_segments_cross(a, b, corners[i], corners[(i + 1) % 4]) for i in range(4))


def _inside(point, rect):
    left, bottom, right, top = rect

    return left <= point[0] <= right and bottom <= point[1] <= top


def _segments_cross(p1, p2, q1, q2):
    # 2 つの線分が交わるか (向きの符号で調べる)
    def side(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    d1, d2 = side(q1, q2, p1), side(q1, q2, p2)
    d3, d4 = side(p1, p2, q1), side(p1, p2, q2)

    return (d1 * d2 <= 0) and (d3 * d4 <= 0)


def _length(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _distance_to_segment(point, a, b):
    px, py = point
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length_squared = dx * dx + dy * dy
    if length_squared == 0.0:
        return math.hypot(px - ax, py - ay)

    # 線分の上で point にいちばん近い位置 (0 = a、1 = b)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_squared))

    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))
