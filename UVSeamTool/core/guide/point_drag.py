"""
ガイドの点 1 つをドラッグで動かす間の計算。
"""

from __future__ import annotations

from dataclasses import replace

from ..path.path_trees import path_tree
from .guide_point import vertex_point
from .guide_segment import GuideSegment, SHORTEST


class PointDrag:
    """ガイドの index 番目の点を、別の頂点へ動かしたガイドを求める。

    前と後の点 (動かない点) からの PathTree をドラッグの始めに 1 回だけ作り、マウスを動かすたびには木をたどるだけに
    する。グラフは向きが無いので、後の点 -> 新しい位置 の道を逆にすれば 新しい位置 -> 後の点 の区間になる。
    閉じたガイドは端で折り返す (最初の点の前は最後の点)。surface は表面 (TargetMesh。graph() を使う)。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, guide, surface, index):
        points   = guide.points
        count    = len(points)
        before   = (index - 1) % count if guide.closed or index > 0 else None
        after    = (index + 1) % count if guide.closed or index + 1 < count else None
        graph    = surface.graph()

        self._guide             = guide
        self._index             = index
        self._before_segment    = before                         # 前の区間の番号 (前の点 -> この点)。無ければ None
        self._before            = path_tree(graph, points[before].vertex) if before is not None else None
        self._after             = path_tree(graph, points[after].vertex) if after is not None else None

    # -- 公開メソッド ---------------------------------------------------------
    def guide(self):
        """動かす前のガイド。"""
        return self._guide

    def index(self):
        return self._index

    def moved(self, point):
        """点を point (GuidePoint。頂点の番号でもよい) へ動かしたガイド。前後の点とつながらなければ None。"""
        point    = vertex_point(point) if isinstance(point, int) else point
        guide    = self._guide
        index    = self._index
        segments = list(guide.segments)

        if self._before is not None:
            path = self._before.pathTo(point.vertex)
            if path is None:
                return None
            segments[self._before_segment] = GuideSegment(mode=SHORTEST, seam=path)

        if self._after is not None:
            path = self._after.pathTo(point.vertex)
            if path is None:
                return None
            segments[index] = GuideSegment(mode=SHORTEST, seam=tuple(reversed(path)))

        points        = list(guide.points)
        points[index] = point

        return replace(guide, points=tuple(points), segments=tuple(segments))
