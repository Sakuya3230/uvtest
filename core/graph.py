# -*- coding: utf-8 -*-
"""
メッシュの頂点とエッジのグラフ (Maya に依存しない)。

    graph = MeshGraph(points, edges)   # points: 頂点の (x, y, z)、edges: エッジごとの (頂点 0, 頂点 1)
    graph.neighbors[v]                 # [(隣の頂点, エッジ, 長さ)]
    graph.edgeBetween(a, b)            # 頂点 a と b を結ぶエッジ (無ければ None)
    graph.matrix()                     # scipy の疎行列 (使えなければ None)
    graph.withPoints(points)           # 位置だけ替えた新しいグラフ (エッジは同じ。段階 13)

エッジの番号はリストの位置 (Maya のエッジの番号と同じ)。重みはエッジの長さ (ワールド)。
UV をカット / 縫合しても頂点・エッジは変わらないので、グラフは作り直さずに使い回せる。
"""
import math

from . import accel
from .picking import PICK_VERTEX

__all__ = ["MeshGraph", "distance"]


def distance(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


class MeshGraph(object):
    """頂点とエッジのグラフ。"""

    def __init__(self, points, edges):
        self.points = list(points)
        self.edges = [tuple(edge) for edge in edges]
        # 探索の内側のループで速く読めるよう、座標は x / y / z の別のリストにも持つ
        xs = self.xs = [p[0] for p in self.points]
        ys = self.ys = [p[1] for p in self.points]
        zs = self.zs = [p[2] for p in self.points]
        # 関数を呼ばずに式で書く (distance を呼ぶより 2 倍ほど速い。numpy はリストとの変換で遅くなった)
        sqrt = math.sqrt
        self.lengths = [sqrt((xs[a] - xs[b]) ** 2 + (ys[a] - ys[b]) ** 2 + (zs[a] - zs[b]) ** 2)
                        for a, b in self.edges]
        self._neighbors = None     # 頂点 -> [(隣の頂点, エッジ, 長さ)] (neighbors で作る)
        self._edge_lookup = None   # (小さい頂点, 大きい頂点) -> エッジ (edgeBetween で作る)
        self._matrix = None        # scipy の疎行列 (matrix で作る)
        # このグラフから作ったもの (曲がりの重みの状態のつながりなど。段階 15)。位置が変わると
        # withPoints で新しいグラフになるので、一緒に捨てられる
        self.cache = {}

    @property
    def neighbors(self):
        """頂点 -> [(隣の頂点, エッジ, 長さ)] (Python の A* が使う。最初に使うときに作る)。

        長さも入れておき、探索のループの中で引かずに済ませる。グラフを作る時間の半分ほどかかる
        (4.5 万頂点で 50 ms) ので、使うときまで作らない。scipy で探すときは使わない
        (位置が変わるたびに作り直すと、再生・移動の間に重くなるため。段階 13)。
        """
        if self._neighbors is None:
            neighbors = [[] for _ in self.points]
            lengths = self.lengths
            for edge, (a, b) in enumerate(self.edges):
                length = lengths[edge]
                neighbors[a].append((b, edge, length))
                neighbors[b].append((a, edge, length))
            self._neighbors = neighbors
        return self._neighbors

    def withPoints(self, points):
        """頂点の位置だけを替えた新しいグラフ (エッジの番号・つながりは同じ。段階 13)。

        変形・移動で位置が変わったときに使う。エッジの両端を Maya から読み直さずに済む
        (読み直しがグラフを作る時間のほとんど)。長さと隣接リストは新しい位置で作り直す。
        """
        if len(points) != len(self.points):
            raise ValueError("頂点の数が違います ({} -> {})".format(len(self.points), len(points)))
        return MeshGraph(points, self.edges)

    def endpoints(self, waypoint):
        """端点 (core.path.Waypoint) の頂点 (頂点なら 1 つ、エッジなら両端)。"""
        if waypoint.kind == PICK_VERTEX:
            return [waypoint.index]
        return list(self.edges[waypoint.index])

    def edgeBetween(self, a, b):
        """頂点 a と b を結ぶエッジの番号 (無ければ None)。表は最初に使うときに 1 回だけ作る。"""
        if self._edge_lookup is None:
            self._edge_lookup = {(min(p, q), max(p, q)): e for e, (p, q) in enumerate(self.edges)}
        return self._edge_lookup.get((min(a, b), max(a, b)))

    def matrix(self):
        """scipy の疎行列 (CSR。頂点 x 頂点、値はエッジの長さ。両向き)。使えなければ None。

        scipy.sparse.csgraph.dijkstra に渡す。最初に使うときに 1 回だけ作る (4.5 万頂点で 40 ms ほど)。
        長さ 0 のエッジは疎行列では「辺が無い」になってしまうので、ごく小さい値にする。
        同じ 2 頂点を結ぶエッジが 2 本あると長さが足されてしまう (普通のメッシュでは起きない)。
        """
        modules = accel.scipy_modules()
        if modules is None:
            return None
        if self._matrix is None:
            numpy, sparse = modules[0], modules[1]
            count = len(self.points)
            if self.edges:
                pairs = numpy.asarray(self.edges, dtype=numpy.int64)
                lengths = numpy.maximum(numpy.asarray(self.lengths, dtype=numpy.float64), 1e-12)
                rows = numpy.concatenate([pairs[:, 0], pairs[:, 1]])
                cols = numpy.concatenate([pairs[:, 1], pairs[:, 0]])
                values = numpy.concatenate([lengths, lengths])
            else:
                rows = cols = numpy.zeros(0, dtype=numpy.int64)
                values = numpy.zeros(0)
            self._matrix = sparse.csr_matrix((values, (rows, cols)), shape=(count, count))
        return self._matrix
