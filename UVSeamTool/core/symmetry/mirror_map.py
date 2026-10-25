"""
対称の対応表 (頂点・エッジの反対側)。Maya には触らない。
"""

from __future__ import annotations

from ...compat.accel import np, spatial

AXES = {"x": 0, "y": 1, "z": 2}


class MirrorMap:
    """頂点とエッジの反対側の番号 (見つからなければ -1)。面の上の頂点・エッジは自分自身。

    反対側は位置で決める: 頂点を対称の面で鏡に写した位置から、許容値の中でいちばん近い頂点。
    エッジは両端の反対側を結ぶエッジ。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, positions, edges, axis, tolerance):
        positions               = np.asarray(positions, dtype=float)
        edges                   = np.asarray(edges, dtype=np.int64)
        mirrored                = positions.copy()
        mirrored[:, AXES[axis]] *= -1.0

        # 頂点: 鏡に写した位置にいちばん近い頂点 (許容値より遠ければ -1)
        distances, nearest      = spatial.cKDTree(positions).query(mirrored, distance_upper_bound=tolerance)
        vertex_map              = np.where(np.isfinite(distances), nearest, -1).astype(np.int64)

        # エッジ: 両端の反対側の組を、(小さい番号, 大きい番号) を 1 つの整数にした鍵で探す
        base                    = len(positions) + 1
        keys                    = np.minimum(edges[:, 0], edges[:, 1]) * base + np.maximum(edges[:, 0], edges[:, 1])
        order                   = np.argsort(keys)
        a, b                    = vertex_map[edges[:, 0]], vertex_map[edges[:, 1]]
        wanted                  = np.minimum(a, b) * base + np.maximum(a, b)
        slots                   = np.clip(np.searchsorted(keys[order], wanted), 0, len(keys) - 1)
        hit                     = (a >= 0) & (b >= 0) & (keys[order][slots] == wanted)

        self._axis              = axis
        self._vertex_map        = vertex_map
        self._edge_map          = np.where(hit, order[slots], -1).astype(np.int64)

    # -- 公開メソッド ---------------------------------------------------------
    def axis(self):
        return self._axis

    def vertex(self, vertex):
        """頂点の反対側の番号 (見つからなければ -1)。"""
        return int(self._vertex_map[vertex])

    def edge(self, edge):
        """エッジの反対側の番号 (見つからなければ -1)。"""
        return int(self._edge_map[edge])

    def edges(self, edges):
        """エッジの列の反対側 (見つかったものだけ, 見つからなかった数)。"""
        mirrored = [int(self._edge_map[edge]) for edge in edges]
        found    = [edge for edge in mirrored if edge >= 0]

        return found, len(mirrored) - len(found)

    def unmatchedVertexCount(self):
        """反対側が見つからない頂点の数 (形が左右でずれていると増える)。"""
        return int(np.count_nonzero(self._vertex_map < 0))
