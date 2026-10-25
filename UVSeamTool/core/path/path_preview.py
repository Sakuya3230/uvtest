"""
プレビュー用の最短パス (同じ始点の PathTree を使い回す)。
"""

from __future__ import annotations

from .path_trees import path_tree


class PathPreview:
    """始点からマウスの下までの最短パスを、何度でも速く求める。

    始点が前と同じなら、前に作った PathTree をそのまま使う (マウスを動かすたびに dijkstra を解かない)。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, graph):
        self._graph = graph
        self._tree  = None

    # -- 公開メソッド ---------------------------------------------------------
    def path(self, start, goal):
        """start から goal までの頂点の列。つながっていなければ None。"""
        if self._tree is None or self._tree.start() != start:
            self._tree = path_tree(self._graph, start)

        return self._tree.pathTo(goal)
