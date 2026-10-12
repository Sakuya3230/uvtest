# -*- coding: utf-8 -*-
"""
最短パス (Maya に依存しない)。

    tree = path_tree(graph, Waypoint("edge", 12))   # スタートを決めたときに 1 回
    path = tree.pathTo(Waypoint("vertex", 300))     # ホバーのたびに (PathResult か None)

PathTree は「スタートから探した結果」を持ち、ゴールごとの道を返す。中身は 2 通り:

    ScipyPathTree   scipy があるとき。作るときに scipy.sparse.csgraph.dijkstra でスタートから
                    全頂点までの最短距離と「ひとつ前の頂点」を 1 回で求める (4.5 万頂点で 7〜11 ms)。
                    pathTo はゴールから前の頂点をたどるだけ (ほぼ 0 ms)
    PythonPathTree  scipy が無いとき。pathTo のたびに A* (shortest_path) で探し、ゴールごとに覚える
                    (4.5 万頂点の極から極で 50〜60 ms)

どちらも同じ長さの最短パスを返す (同じ長さの道が複数あると、選ぶ道は違いうる)。

端点がエッジのとき:
    スタートがエッジ  両端の頂点から同時に (距離 0 で) 探し始め、そのエッジもパスに含める
    エンドがエッジ    どちらかの端に着けばゴール (近いほう)。そのエッジもパスに含める
両端から同時に始めるので、パスがスタートのエッジ自体を通ることはない (エンドも同じ)。
"""
import heapq
import math

from . import accel
from .picking import PICK_EDGE, PICK_VERTEX

__all__ = ["Waypoint", "PathResult", "shortest_path", "PathTree", "PythonPathTree",
           "ScipyPathTree", "path_tree"]


class Waypoint(object):
    """パスの端点 (スタート / エンド)。頂点かエッジ。"""

    def __init__(self, kind, index):
        self.kind = kind     # PICK_VERTEX / PICK_EDGE
        self.index = index

    def key(self):
        return (self.kind, self.index)

    def __eq__(self, other):
        return isinstance(other, Waypoint) and self.key() == other.key()

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.key())

    def __repr__(self):
        return "Waypoint({!r}, {})".format(self.kind, self.index)


class PathResult(object):
    """最短パス。"""

    def __init__(self, vertices, edges, length, cost=None):
        self.vertices = vertices   # 頂点の列 (端から端までの折れ線の順)
        self.edges = edges         # エッジの列 (同じ順。vertices より 1 つ少ない)
        self.length = length       # 長さ (エッジの長さの和)
        # 探したときのコスト (曲がりの重みがあれば長さ + 曲がり。段階 15。無ければ長さ)
        self.cost = length if cost is None else cost

    def __repr__(self):
        return "PathResult({} 本, length={:.4f})".format(len(self.edges), self.length)


def _same(graph, start):
    """スタートとエンドが同じとき: 頂点ならエッジの無いパス、エッジならそのエッジ 1 本。"""
    if start.kind == PICK_VERTEX:
        return PathResult([start.index], [], 0.0)
    a, b = graph.edges[start.index]
    return PathResult([a, b], [start.index], graph.lengths[start.index])


def _finish(graph, start, goal, vertices, edges):
    """頂点からの道に、端点のエッジ (スタートは先頭、エンドは末尾) を足して PathResult にする。"""
    if start.kind == PICK_EDGE:
        a, b = graph.edges[start.index]
        vertices.insert(0, b if vertices[0] == a else a)
        edges.insert(0, start.index)
    if goal.kind == PICK_EDGE:
        a, b = graph.edges[goal.index]
        vertices.append(b if vertices[-1] == a else a)
        edges.append(goal.index)
    return PathResult(vertices, edges, sum(graph.lengths[e] for e in edges))


def shortest_path(graph, start, goal):
    """start から goal (どちらも Waypoint) までの最短パス (PathResult)。無ければ None (Python の A*)。

    A* は「スタートからの距離 + ゴールまでの直線距離 (見積もり)」の小さい順に頂点を調べる。
    エッジの長さの和は直線距離より短くならないので、最短が保証される。ゴールに着いたら打ち切る。

    速さのため、内側のループは関数を呼ばずに書く (隣接リストに長さを入れ、座標は x / y / z の
    別のリスト、ゴールの座標は変数に取り出しておく。旧版で 84 -> 49 ms)。ゴールの候補は 1 つか 2 つ
    (エッジの両端)。距離の 2 乗の小さいほうを選んでから、平方根を 1 回だけ取る。
    """
    if start == goal:
        return _same(graph, start)
    sources = graph.endpoints(start)
    targets = graph.endpoints(goal)
    target_set = set(targets)
    xs, ys, zs = graph.xs, graph.ys, graph.zs
    ax, ay, az = xs[targets[0]], ys[targets[0]], zs[targets[0]]
    bx, by, bz = xs[targets[-1]], ys[targets[-1]], zs[targets[-1]]
    neighbors = graph.neighbors
    sqrt = math.sqrt
    push, pop = heapq.heappush, heapq.heappop
    infinity = float("inf")

    best = {}       # 頂点 -> スタートからの距離
    previous = {}   # 頂点 -> (前の頂点, 通ったエッジ)
    queue = []
    for source in sources:
        best[source] = 0.0
        previous[source] = None
        push(queue, (0.0, 0.0, source))   # 最初に取り出すので、見積もりは 0 でよい
    reached = None
    while queue:
        _estimate, so_far, vertex = pop(queue)
        if so_far > best[vertex]:
            continue   # もっと短い道で取り出し済み
        if vertex in target_set:
            reached = vertex
            break
        for neighbor, edge, length in neighbors[vertex]:
            total = so_far + length
            if total < best.get(neighbor, infinity):
                best[neighbor] = total
                previous[neighbor] = (vertex, edge)
                x, y, z = xs[neighbor], ys[neighbor], zs[neighbor]
                da = (x - ax) * (x - ax) + (y - ay) * (y - ay) + (z - az) * (z - az)
                db = (x - bx) * (x - bx) + (y - by) * (y - by) + (z - bz) * (z - bz)
                push(queue, (total + sqrt(da if da < db else db), total, neighbor))
    if reached is None:
        return None
    vertices, edges = [reached], []
    while previous[vertices[-1]] is not None:
        vertex, edge = previous[vertices[-1]]
        vertices.append(vertex)
        edges.append(edge)
    vertices.reverse()
    edges.reverse()
    return _finish(graph, start, goal, vertices, edges)


class PathTree(object):
    """スタートから探した結果。pathTo(goal) でゴールまでの最短パス (PathResult か None)。"""

    backend = ""   # "scipy" / "python" (ログ・テスト用)

    def __init__(self, graph, start):
        self.graph = graph
        self.start = start

    def pathTo(self, goal):
        raise NotImplementedError


class PythonPathTree(PathTree):
    """scipy が無いとき: ゴールごとに A* で探して覚える。"""

    backend = "python"

    def __init__(self, graph, start):
        super().__init__(graph, start)
        self._paths = {}   # ゴールの key -> PathResult か None

    def pathTo(self, goal):
        key = goal.key()
        if key not in self._paths:
            self._paths[key] = shortest_path(self.graph, self.start, goal)
        return self._paths[key]


class ScipyPathTree(PathTree):
    """scipy があるとき: スタートから全頂点までを 1 回で探し、ゴールへは前の頂点をたどる。

    csgraph.dijkstra(行列, indices=始点のリスト, return_predecessors=True, min_only=True) は、
    始点のどれかからの最短距離 (dist)・ひとつ前の頂点 (predecessors。始点と届かない頂点は -9999)
    を返す。スタートがエッジなら、両端を始点にする (どちらか近いほうから)。
    """

    backend = "scipy"
    _NONE = -9999   # predecessors の「前が無い」

    def __init__(self, graph, start):
        super().__init__(graph, start)
        modules = accel.scipy_modules()
        csgraph = modules[2]
        result = csgraph.dijkstra(graph.matrix(), directed=True, indices=graph.endpoints(start),
                                  return_predecessors=True, min_only=True)
        self._dist = result[0]
        self._previous = result[1]

    def distance(self, vertex):
        """スタートから頂点までの最短距離 (届かなければ inf)。"""
        return float(self._dist[vertex])

    def pathTo(self, goal):
        if goal == self.start:
            return _same(self.graph, self.start)
        # エッジのゴールは、近いほうの端まで (A* が先に着くほう)
        reached = min(self.graph.endpoints(goal), key=self.distance)
        if math.isinf(self.distance(reached)):
            return None   # つながっていない
        vertices = [reached]
        previous = self._previous
        while previous[vertices[-1]] != self._NONE:
            vertices.append(int(previous[vertices[-1]]))
        vertices.reverse()
        edges = [self.graph.edgeBetween(a, b) for a, b in zip(vertices, vertices[1:])]
        return _finish(self.graph, self.start, goal, vertices, edges)


def path_tree(graph, start, use_scipy=None, turn_weight=0.0):
    """スタートからの PathTree。use_scipy を省くと、scipy が使えれば ScipyPathTree。

    turn_weight (曲がりの重み) が 0 より大きければ、core.turning の曲がりを数える版 (段階 15)。
    """
    if turn_weight > 0.0:
        from .turning import turn_path_tree   # turning は path を import するので、ここで
        return turn_path_tree(graph, start, turn_weight, use_scipy)
    if use_scipy is None:
        use_scipy = accel.available()
    if use_scipy:
        return ScipyPathTree(graph, start)
    return PythonPathTree(graph, start)
