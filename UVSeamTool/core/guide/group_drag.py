"""
選んだ複数の点をまとめて動かす (docs/27_shortest_only.md)。

つかんだ点の移動量 (オブジェクト空間) を、選んだほかの点にも足して、いちばん近い頂点へ。1 点のドラッグは
core.guide.point_drag。
"""

from __future__ import annotations

from dataclasses import replace

from .guide_point import vertex_point
from .segment_modes import moved_segments, resolve
from .set_editing import find_guide


class GroupDrag:
    """ガイドの組の点 points ({(ガイドの id, 点の番号)}) を、grabbed の点の動きに合わせてまとめて動かす。

    ほかの点は、元の位置 + つかんだ点の移動量 にいちばん近い頂点へ。動いた点を端に持つ区間は最短パスで求め直す。
    surface は表面 (TargetMesh。graph() と nearestVertexTo を使う)。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, guide_set, surface, points, grabbed):
        positions       = surface.graph().positions()
        self._guide_set = guide_set
        self._surface   = surface
        self._points    = sorted(points)
        self._grabbed   = grabbed
        self._start     = positions[find_guide(guide_set, grabbed[0]).points[grabbed[1]].vertex]
        self._origins   = {key: positions[find_guide(guide_set, key[0]).points[key[1]].vertex] for key in self._points}

    # -- 公開メソッド ---------------------------------------------------------
    def guideSet(self):
        """動かす前のガイドの組。"""
        return self._guide_set

    def grabbed(self):
        """つかんだ点 (ガイドの id, 点の番号)。"""
        return self._grabbed

    def moved(self, point):
        """つかんだ点を point (GuidePoint) へ動かした組。つながらない区間があれば None。"""
        offset = self._surface.graph().positions()[point.vertex] - self._start
        moved  = {key: vertex_point(self._surface.nearestVertexTo(self._origins[key] + offset))
                  for key in self._points if key != self._grabbed}
        moved[self._grabbed] = point

        result = self._guide_set
        for guide_id in sorted({guide_id for guide_id, _ in self._points}):
            guide  = find_guide(result, guide_id)
            points = {i: p for (g, i), p in moved.items() if g == guide_id}
            work   = replace(guide, points=tuple(points.get(i, p) for i, p in enumerate(guide.points)))
            work   = resolve(work, moved_segments(work, set(points)), self._surface)
            if work is None:
                return None
            result = replace(result, guides=tuple(work if g.id == guide_id else g for g in result.guides))

        return result

