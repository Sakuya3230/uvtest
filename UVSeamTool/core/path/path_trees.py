"""
始点から全頂点への最短パスの木を作る (グラフのまっすぐさの重みで、ふつうの木か曲がりを数える木かを選ぶ)。
"""

from __future__ import annotations

from .path_tree import PathTree
from .turn_path_tree import TurnPathTree


def path_tree(graph, start):
    """start からの最短パスの木。graph.turnWeight() が 0 より大きければ曲がりも数える (TurnPathTree)。

    どちらも start() / pathTo(goal) を持つ。最短パスを求める所 (プレビュー・区間を求める・点のドラッグ) はここから作る。
    """
    weight = graph.turnWeight()
    if weight > 0.0:
        return TurnPathTree(graph, start, weight)

    return PathTree(graph, start)
