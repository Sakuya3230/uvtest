"""
1 つの始点から全頂点への最短パス (dijkstra を 1 回だけ解いて使い回す)。
"""

from __future__ import annotations

from ...compat.accel import csgraph

_NO_PREDECESSOR = -9999   # scipy が「前の頂点が無い」に使う値


class PathTree:
    """始点から全頂点への最短パスの木。

    作るときに dijkstra を 1 回だけ解き、各頂点の「1 つ前の頂点」(predecessors) を持つ。
    どの頂点へのパスも、そこから前の頂点をたどるだけで求まる (マウスを動かすたびに解き直さない)。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, graph, start):
        _, predecessors = csgraph.dijkstra(graph.matrix(), indices=start, return_predecessors=True)

        self._start         = start
        self._predecessors  = predecessors

    # -- 公開メソッド ---------------------------------------------------------
    def start(self):
        return self._start

    def pathTo(self, goal):
        """始点から goal までの頂点の列 (両端を含む tuple)。つながっていなければ None。"""
        if goal == self._start:
            return (goal,)

        if self._predecessors[goal] == _NO_PREDECESSOR:
            return None

        # goal から前の頂点をたどって始点まで戻り、逆にする
        vertices = [goal]
        while vertices[-1] != self._start:
            vertices.append(int(self._predecessors[vertices[-1]]))

        return tuple(reversed(vertices))
