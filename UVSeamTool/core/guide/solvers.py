"""
区間の作り方 -> 区間の頂点の列を求める関数 の表。

作り方を足すときは、関数を書いてこの表に 1 行足す (版 1 は最短だけ)。
"""

from __future__ import annotations

from ..path.shortest_path import shortest_path
from .guide_segment import SHORTEST


def solve_shortest(graph, start_point, end_point):
    return shortest_path(graph, start_point.vertex, end_point.vertex)


SOLVERS = {
    SHORTEST: solve_shortest,
}


def solve(mode, graph, start_point, end_point):
    """区間の頂点の列 (tuple)。求められなければ None。"""
    return SOLVERS[mode](graph, start_point, end_point)
