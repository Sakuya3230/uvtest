"""
メッシュのつながり (頂点 = 節、エッジ = 重みが長さの辺)。

utils.mesh.Mesh が読んだ配列から作る。Maya には触らない。
"""

from __future__ import annotations

from ...compat.accel import np, sparse


class MeshGraph:
    """メッシュの頂点のつながり。

    最短パスに渡す疎行列 (重み = エッジの長さ。weights を渡せばその重み) と、頂点の組からエッジの番号を引く表を持つ。
    まっすぐさの重み (turnWeight。0 なら長さだけの最短) も持ち、最短パスの木 (path_trees.path_tree) はこれを見て作る
    (区間を求める所すべてに重みを渡して回らなくてよいように)。
    グラフから作った重いもの (曲がりを数えるためのつながりなど) は cached で覚える (位置が変われば新しいグラフになり、一緒に捨てる)。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, positions, edges, turn_weight=0.0, weights=None):
        lengths             = np.linalg.norm(positions[edges[:, 0]] - positions[edges[:, 1]], axis=1)
        weights             = lengths if weights is None else np.asarray(weights, dtype=float)
        count               = len(positions)
        # 向きの無いグラフにするため、両向きの辺を入れる
        rows                = np.concatenate([edges[:, 0], edges[:, 1]])
        columns             = np.concatenate([edges[:, 1], edges[:, 0]])

        self._positions     = positions
        self._edges         = edges
        self._weights       = weights
        self._matrix        = sparse.csr_matrix((np.concatenate([weights, weights]), (rows, columns)), shape=(count, count))
        self._edge_of       = {_key(a, b): index for index, (a, b) in enumerate(edges.tolist())}
        self._turn_weight   = float(turn_weight)
        self._cache         = {}

    # -- 公開メソッド ---------------------------------------------------------
    def vertexCount(self):
        return len(self._positions)

    def positions(self):
        """頂点の位置 (頂点の数 x 3 の numpy の配列)。"""
        return self._positions

    def edges(self):
        """エッジの両端の頂点 (エッジの数 x 2 の numpy の配列)。"""
        return self._edges

    def edgeWeights(self):
        """エッジごとの重み (エッジの数,)。ふつうは長さ (weights を渡したグラフはその重み)。"""
        return self._weights

    def matrix(self):
        """scipy の疎行列 (csgraph に渡す)。"""
        return self._matrix

    def edgeBetween(self, a, b):
        """頂点 a と b を結ぶエッジの番号 (つながっていなければ None)。"""
        return self._edge_of.get(_key(a, b))

    def turnWeight(self):
        """まっすぐさの重み (0 なら長さだけの最短パス)。"""
        return self._turn_weight

    def setTurnWeight(self, weight):
        self._turn_weight = float(weight)

    def cached(self, key, factory):
        """key で覚えたもの。無ければ factory() で作って覚える。"""
        if key not in self._cache:
            self._cache[key] = factory()

        return self._cache[key]


def _key(a, b):
    return (a, b) if a < b else (b, a)
