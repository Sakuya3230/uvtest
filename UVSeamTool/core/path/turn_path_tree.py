"""
曲がりの少ないパスを選ぶ最短パス (まっすぐさ。1 つの始点から全頂点へ、dijkstra を 1 回)。
"""

from __future__ import annotations

import math

from ...compat.accel import csgraph, np, sparse

_TINY           = 1e-12     # 疎行列では 0 が「辺が無い」になるので、コスト 0 の辺はごく小さい値にする
_NO_PREDECESSOR = -9999     # scipy が「前の状態が無い」に使う値


class TurnPathTree:
    """始点から全頂点への、曲がりにもコストを付けた最短パスの木 (path_tree.PathTree と同じ使い方)。

        1 歩のコスト = エッジの重み (graph.edgeWeights。ふつうは長さ) + 重み × 平均のエッジの長さ × (1 - cos 曲がり角)

    まっすぐ進めば 0、直角に曲がれば「重み × 平均の長さ」(重み 1 = 直角 1 回はエッジ 1 本ぶんの遠回りと同じ)、
    鋭く折り返すほど大きい (最大 2 倍)。平均の長さを掛けるので、メッシュの大きさ (単位) によらず同じ重みが同じように効く。

    曲がり角は「どのエッジから来たか」で決まるので、頂点ではなく「向き付きのエッジ」(状態。エッジ e を a -> b なら 2e、
    b -> a なら 2e + 1) を節にして探す。状態のつながり (着いた頂点から出ていくエッジへ。U ターンは除く) は
    グラフごとに 1 回だけ作る (MeshGraph.cached)。始点の頂点から出ていく状態へは、仮の始点からそのエッジの長さの辺を張り、
    仮の始点から dijkstra を 1 回だけ解く。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, graph, start, weight):
        steps = graph.cached("turnSteps", lambda: _turn_steps(graph))
        count = steps["count"]
        first = np.nonzero(steps["tails"] == start)[0]   # 始点から出ていく状態
        costs = np.maximum(steps["weights"][steps["targets"]] + weight * steps["scale"] * steps["bends"], _TINY)

        # 仮の始点 (番号 count) -> 最初の状態 (コスト = そのエッジの長さ) を足した疎行列
        rows    = np.concatenate([steps["sources"], np.full(len(first), count, dtype=np.int64)])
        columns = np.concatenate([steps["targets"], first])
        values  = np.concatenate([costs, np.maximum(steps["weights"][first], _TINY)])
        matrix  = sparse.csr_matrix((values, (rows, columns)), shape=(count + 1, count + 1))
        distances, predecessors = csgraph.dijkstra(matrix, directed=True, indices=count, return_predecessors=True)

        self._start         = start
        self._steps         = steps
        self._distances     = distances
        self._predecessors  = predecessors

    # -- 公開メソッド ---------------------------------------------------------
    def start(self):
        return self._start

    def pathTo(self, goal):
        """始点から goal までの頂点の列 (両端を含む tuple)。つながっていなければ None。"""
        if goal == self._start:
            return (goal,)

        # goal に着く状態のうち、いちばん安いもの
        arrivals = np.nonzero(self._steps["heads"] == goal)[0]
        if len(arrivals) == 0:
            return None

        state = int(arrivals[np.argmin(self._distances[arrivals])])
        if math.isinf(self._distances[state]):
            return None

        # 前の状態をたどって仮の始点まで戻り、逆にする
        count  = self._steps["count"]
        states = [state]
        while True:
            before = int(self._predecessors[states[-1]])
            if before in (count, _NO_PREDECESSOR):
                break
            states.append(before)
        states.reverse()

        heads = self._steps["heads"]
        return (self._start,) + tuple(int(heads[state]) for state in states)


def _turn_steps(graph):
    # 状態のつながり (sources -> targets) と曲がりの量 (1 - cos)。グラフごとに 1 回 (ループなしで numpy でまとめて作る)
    positions   = graph.positions()
    edges       = graph.edges()
    count       = 2 * len(edges)

    # 状態 2e = a -> b、2e + 1 = b -> a の出る頂点 (tails) と着く頂点 (heads)
    tails       = np.empty(count, dtype=np.int64)
    heads       = np.empty(count, dtype=np.int64)
    tails[0::2], heads[0::2] = edges[:, 0], edges[:, 1]
    tails[1::2], heads[1::2] = edges[:, 1], edges[:, 0]
    vectors     = positions[heads] - positions[tails]
    lengths     = np.linalg.norm(vectors, axis=1)
    weights     = np.repeat(graph.edgeWeights(), 2)   # 進むコスト (ふつうは長さ。谷のグラフは谷ほど安い)
    units       = vectors / np.where(lengths > 0.0, lengths, 1.0)[:, None]

    # 状態 p の次の候補は「p の着く頂点から出る状態」すべて。出る頂点の順に並べた表から、範囲をまとめて取り出す
    order       = np.argsort(tails, kind="stable")
    out_count   = np.bincount(tails, minlength=len(positions))
    out_start   = np.concatenate([[0], np.cumsum(out_count)[:-1]])
    successors  = out_count[heads]
    sources     = np.repeat(np.arange(count), successors)
    offsets     = np.arange(len(sources)) - np.repeat(np.cumsum(successors) - successors, successors)
    targets     = order[np.repeat(out_start[heads], successors) + offsets]
    keep        = targets != (sources ^ 1)   # U ターン (来たエッジを戻る) は除く
    sources     = sources[keep]
    targets     = targets[keep]
    bends       = np.maximum(1.0 - (units[sources] * units[targets]).sum(axis=1), 0.0)

    return {"count": count, "tails": tails, "heads": heads, "weights": weights, "sources": sources,
            "targets": targets, "bends": bends, "scale": float(lengths.mean()) if len(lengths) else 0.0}
