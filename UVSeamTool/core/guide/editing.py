"""
ガイドの編集。どの関数も元のガイドは変えず、新しいガイドを返す。

閉じたガイド (closed) は、区間の数が点の数と同じで、最後の区間は最後の点から最初の点へ戻る。
"""

from __future__ import annotations

from dataclasses import replace

from .guide import Guide
from .guide_point import vertex_point
from .guide_segment import GuideSegment, SHORTEST
from .solvers import solve


def new_guide(guide_id, vertex):
    """点が 1 つだけのガイド (区間はまだ無い)。"""
    return Guide(id=guide_id, points=(vertex_point(vertex),))


def add_point(guide, graph, vertex, mode=SHORTEST):
    """端に点を足し、最後の点からの区間を求めたガイド。区間を求められなければ None。"""
    point    = vertex_point(vertex)
    vertices = solve(mode, graph, guide.points[-1], point)
    if vertices is None:
        return None

    segment = GuideSegment(mode=mode, seam=vertices)

    return replace(guide, points=guide.points + (point,), segments=guide.segments + (segment,))


def remove_last_point(guide):
    """最後の点と、そこへの区間を消したガイド (点が 2 つ以上のときに使う)。"""
    return replace(guide, points=guide.points[:-1], segments=guide.segments[:-1])


def insert_point(guide, segment_index, vertex):
    """segment_index 番目の区間が通る vertex に点を挿入したガイド。

    区間の頂点の列を vertex で 2 つに分けるだけ (求め直さない。作り方もそのまま)。vertex が区間の途中に無ければ None。
    挿入した点の番号は segment_index + 1 (閉じたガイドの最後の区間なら、点の列の最後)。
    """
    segment  = guide.segments[segment_index]
    vertices = segment.seam
    if vertex not in vertices[1:-1]:
        return None

    cut      = vertices.index(vertex)
    first    = replace(segment, seam=vertices[:cut + 1])
    second   = replace(segment, seam=vertices[cut:])
    points   = guide.points[:segment_index + 1] + (vertex_point(vertex),) + guide.points[segment_index + 1:]
    segments = guide.segments[:segment_index] + (first, second) + guide.segments[segment_index + 1:]

    return replace(guide, points=points, segments=segments)
