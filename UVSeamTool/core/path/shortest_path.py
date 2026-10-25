"""
頂点から頂点への最短パス (scipy の dijkstra)。
"""

from __future__ import annotations

from .path_trees import path_tree


def shortest_path(graph, start, goal):
    """start から goal までの頂点の列 (両端を含む tuple)。つながっていなければ None。

    1 回だけ求めるとき用。同じ始点から何度も求めるときは path_trees.path_tree の木を持って使い回す。
    グラフのまっすぐさの重みが 0 より大きければ、曲がりの少ないパス (TurnPathTree)。
    """
    return path_tree(graph, start).pathTo(goal)
