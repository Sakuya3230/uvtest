# -*- coding: utf-8 -*-
"""
対称の対応表 (Maya に依存しない。段階 17)。

    mirror = MirrorMap(points, edges, axis_index=0, tolerance=0.1)
    mirror.vertex[v]            頂点 v の反対側の頂点 (見つからなければ -1。面の上の頂点は自分)
    mirror.edge[e]              エッジ e の反対側のエッジ (見つからなければ -1)
    edges, missing = mirror.edges([3, 4, 5])   反対側のエッジ (見つからないものは除く) と、その数
    mirror.waypoint(Waypoint("edge", 3))       端点の反対側 (無ければ None)
    with_mirror(edges, mirror)                 エッジ + 反対側 (重複なし、元の順を先に)

反対側は位置で決める (トポロジーは使わない):
- 頂点を対称の面 (原点を通り、軸に垂直) で鏡映した点から、tolerance 以内で最も近い頂点
- エッジは、両端の頂点の反対側どうしを結ぶエッジ

探し方は 2 通り (結果は同じ。同じ距離の頂点が 2 つあるときだけ、選ぶものが違いうる):
    scipy があるとき  scipy.spatial.cKDTree.query(鏡映した点, distance_upper_bound=tolerance)。
                      4.5 万頂点で数十 ms
    無いとき          格子 (旧版と同じ)。マスを許容値にすると細かいメッシュで 1 マスに何十もの頂点が
                      入り 4.5 万頂点で 10 秒かかったので、2 回に分ける:
                        1 回目  平均のエッジの長さの 1/4 (許容値より大きければ許容値) のマス
                                (ここで見つかれば、許容値の中で最も近い頂点)
                        2 回目  見つからなかった頂点だけ、許容値のマスで (fallback_limit 個まで)
"""
import math

from . import accel
from .picking import PICK_VERTEX

__all__ = ["AXES", "SPACES", "MirrorMap", "with_mirror", "DEFAULT_TOLERANCE", "FALLBACK_LIMIT"]

AXES = ("x", "y", "z")
SPACES = ("world", "object")
DEFAULT_TOLERANCE = 0.1   # Maya の対称の許容値の既定
FALLBACK_LIMIT = 5000     # 格子の 2 回目で探す頂点の数の上限 (左右が大きくずれたメッシュで固まらない)


def _reflect(points, axis_index):
    reflected = []
    for p in points:
        q = list(p)
        q[axis_index] = -q[axis_index]
        reflected.append(q)
    return reflected


class MirrorMap(object):
    """頂点・エッジの、対称の面の反対側の番号。"""

    def __init__(self, points, edges, axis_index, tolerance=DEFAULT_TOLERANCE, use_scipy=None,
                 fallback_limit=FALLBACK_LIMIT):
        self.axis_index = axis_index
        self.tolerance = max(float(tolerance), 1e-9)
        if use_scipy is None:
            use_scipy = accel.available()
        self.backend = "scipy" if use_scipy else "python"
        if use_scipy:
            self.vertex, self.edge = self._match_scipy(points, edges)
            self.unmatched = self.vertex.count(-1)
            return
        reflected = _reflect(points, axis_index)
        self.vertex = [-1] * len(points)
        self._match_grid(points, edges, reflected, fallback_limit)
        lookup = {}
        for e, (a, b) in enumerate(edges):
            lookup[(a, b) if a < b else (b, a)] = e
        self.edge = []
        for a, b in edges:
            ma, mb = self.vertex[a], self.vertex[b]
            if ma < 0 or mb < 0:
                self.edge.append(-1)
            else:
                self.edge.append(lookup.get((ma, mb) if ma < mb else (mb, ma), -1))
        self.unmatched = self.vertex.count(-1)   # 反対側が見つからない頂点の数

    # -- 探し方 -----------------------------------------------------------------

    def _match_scipy(self, points, edges):
        """(頂点の対応, エッジの対応) を numpy / scipy で (Python のループなし)。

        頂点: 鏡映した点を cKDTree.query (workers=-1 で並列に)。見つからなければ番号が len(points)。
        エッジ: 両端の反対側の組 (小さい番号, 大きい番号) を 1 つの整数の鍵にし、元のエッジの鍵を
        並べたものから searchsorted で探す (辞書を作って 1 本ずつ引くと、9 万エッジで 60 ms かかった)。
        """
        modules = accel.scipy_modules()
        np, spatial = modules[0], modules[3]
        count = len(points)
        if not count:
            return [], [-1] * len(edges)
        coords = np.asarray(points, dtype=np.float64).reshape(-1, 3)
        reflected = coords.copy()
        reflected[:, self.axis_index] *= -1.0
        tree = spatial.cKDTree(coords)
        try:
            _distances, indices = tree.query(reflected, k=1, distance_upper_bound=self.tolerance,
                                             workers=-1)
        except TypeError:   # 古い scipy (workers が無い)
            _distances, indices = tree.query(reflected, k=1, distance_upper_bound=self.tolerance)
        vertex = np.where(indices < count, indices, -1).astype(np.int64)
        if not len(edges):
            return vertex.tolist(), []
        pairs = np.asarray(edges, dtype=np.int64).reshape(-1, 2)
        low, high = pairs.min(axis=1), pairs.max(axis=1)
        keys = low * count + high
        order = np.argsort(keys, kind="stable")
        sorted_keys = keys[order]
        ma, mb = vertex[pairs[:, 0]], vertex[pairs[:, 1]]
        valid = (ma >= 0) & (mb >= 0)
        wanted = np.minimum(ma, mb) * count + np.maximum(ma, mb)
        position = np.clip(np.searchsorted(sorted_keys, wanted), 0, len(sorted_keys) - 1)
        found = valid & (sorted_keys[position] == wanted)
        edge = np.where(found, order[position], -1)
        return vertex.tolist(), edge.tolist()

    def _match_grid(self, points, edges, reflected, fallback_limit):
        tolerance = self.tolerance
        if edges:
            mean = sum(math.sqrt(sum((points[a][k] - points[b][k]) ** 2 for k in range(3)))
                       for a, b in edges) / len(edges)
            fine = min(tolerance, max(mean * 0.25, 1e-9))
        else:
            fine = tolerance
        missing = self._grid_pass(points, reflected, range(len(points)), fine, fine)
        if missing and fine < tolerance:
            self._grid_pass(points, reflected, missing[:fallback_limit], tolerance, tolerance)

    def _grid_pass(self, points, reflected, indices, cell, radius):
        """indices の頂点の反対側を、cell の大きさの格子で radius 以内から探す。見つからなかった頂点。"""
        floor = math.floor
        grid = {}
        for i, (x, y, z) in enumerate(points):
            key = (int(floor(x / cell)), int(floor(y / cell)), int(floor(z / cell)))
            cell_list = grid.get(key)
            if cell_list is None:
                grid[key] = [i]
            else:
                cell_list.append(i)
        limit = radius * radius
        vertex = self.vertex
        missing = []
        for i in indices:
            qx, qy, qz = reflected[i]
            cx, cy, cz = int(floor(qx / cell)), int(floor(qy / cell)), int(floor(qz / cell))
            best, best_d = -1, limit
            for gx in (cx - 1, cx, cx + 1):
                for gy in (cy - 1, cy, cy + 1):
                    for gz in (cz - 1, cz, cz + 1):
                        for j in grid.get((gx, gy, gz), ()):
                            rx, ry, rz = points[j]
                            d = (rx - qx) * (rx - qx) + (ry - qy) * (ry - qy) + (rz - qz) * (rz - qz)
                            if d < best_d or (d == best_d and best < 0):
                                best, best_d = j, d
            vertex[i] = best
            if best < 0:
                missing.append(i)
        return missing

    # -- 引く -------------------------------------------------------------------

    def edges(self, edges):
        """エッジの反対側 (見つからないものは除く) と、見つからなかった数。"""
        mirrored = [self.edge[e] for e in edges]
        return [e for e in mirrored if e >= 0], mirrored.count(-1)

    def waypoint(self, waypoint):
        """端点 (core.path.Waypoint) の反対側。見つからなければ None。"""
        from .path import Waypoint
        table = self.vertex if waypoint.kind == PICK_VERTEX else self.edge
        index = table[waypoint.index]
        return Waypoint(waypoint.kind, index) if index >= 0 else None


def with_mirror(edges, mirror):
    """エッジに反対側を足したもの (重複なし、元のエッジが先) と、反対側が見つからなかった数。

    mirror が None (対称がオフ) なら、元のエッジ (重複なし) と 0。
    """
    result = []
    seen = set()
    for edge in edges:
        if edge not in seen:
            seen.add(edge)
            result.append(edge)
    if mirror is None:
        return result, 0
    mirrored, missing = mirror.edges(result)
    for edge in mirrored:
        if edge not in seen:
            seen.add(edge)
            result.append(edge)
    return result, missing
