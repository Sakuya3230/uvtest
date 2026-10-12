# -*- coding: utf-8 -*-
"""
曲がりの重み付きの最短パス (Maya に依存しない。段階 15)。

    tree = turn_path_tree(graph, Waypoint("vertex", 0), weight=1.0)   # スタートを決めたときに 1 回
    path = tree.pathTo(Waypoint("edge", 12))                          # PathResult (cost も持つ) か None

1 歩のコスト = エッジの長さ + 重み × 平均のエッジの長さ × (1 - cos 曲がり角)
    まっすぐ進めば 0、直角に曲がれば 重み × 平均の長さ、鋭く折り返すほど大きい (最大 2 倍)。
    平均のエッジの長さを掛けるので、メッシュの大きさ (単位) によらず同じ重みで効く。
    重み 0 なら長さだけの最短パス (core.path と同じ。path_tree は重み 0 なら core.path を使う)。

仕組み:
- 曲がり角は「どのエッジから来たか」で決まるので、頂点だけでは状態が足りない。状態を
  「向き付きのエッジ」 (エッジ e を a -> b に進んだら 2e、b -> a なら 2e + 1) にして、
  状態から状態へ (着いた頂点から出ていくエッジへ。来たエッジを戻る U ターンは除く) 探す
- スタートが頂点なら、そこから出ていく向き付きのエッジが最初の状態 (コストはその長さ)。
  スタートがエッジなら、そのエッジの両向きが最初の状態 (コスト 0。パスの先頭はそのエッジ。
  その先の曲がりは、スタートのエッジの向きから測る)
- ゴールが頂点なら、そこに着く状態のどれか (いちばん安いもの)。ゴールがエッジなら、そのエッジを
  通った状態 (最後の曲がりも数える)

    TurnPathTree        scipy があるとき。状態のつながり (向き付きのエッジの数 × 平均の次数ほど) を
                        numpy で作って疎行列にし、csgraph.dijkstra をスタートから 1 回 (仮の始点 S から
                        最初の状態へ、最初のコストの辺を張る)。つながりと曲がりの量はグラフごとに 1 回
    PythonTurnPathTree  scipy が無いとき。ゴールごとに状態の A* (見積もりはゴールまでの直線距離。
                        コストは長さ以上なので最短が保証される)。旧版の Python 版と同じ考え方
"""
import heapq
import math

from . import accel
from .path import PathResult, _same
from .picking import PICK_EDGE, PICK_VERTEX

__all__ = ["turn_scale", "turn_shortest_path", "TurnPathTree", "PythonTurnPathTree",
           "turn_path_tree", "path_cost"]

_TINY = 1e-12   # 疎行列では 0 が「辺が無い」になるので、コスト 0 の辺はごく小さい値にする


def turn_scale(graph):
    """曲がりのコストの単位 (平均のエッジの長さ)。"""
    lengths = graph.lengths
    return sum(lengths) / len(lengths) if lengths else 0.0


def _units(graph):
    """エッジごとの a -> b の単位ベクトル (x, y, z のリスト)。長さ 0 のエッジは 0 ベクトル。"""
    cached = graph.cache.get("turn_units")
    if cached is None:
        ux, uy, uz = [], [], []
        xs, ys, zs = graph.xs, graph.ys, graph.zs
        for (a, b), length in zip(graph.edges, graph.lengths):
            inv = 1.0 / length if length > 0.0 else 0.0
            ux.append((xs[b] - xs[a]) * inv)
            uy.append((ys[b] - ys[a]) * inv)
            uz.append((zs[b] - zs[a]) * inv)
        cached = graph.cache["turn_units"] = (ux, uy, uz)
    return cached


def _head(graph, state):
    """状態 (向き付きのエッジ) の着く頂点。"""
    a, b = graph.edges[state >> 1]
    return a if state & 1 else b


def _tail(graph, state):
    a, b = graph.edges[state >> 1]
    return b if state & 1 else a


def _first_states(graph, start):
    """スタートの [(状態, コスト)]。"""
    if start.kind == PICK_EDGE:
        return [(2 * start.index, 0.0), (2 * start.index + 1, 0.0)]
    result = []
    for _neighbor, edge, length in graph.neighbors[start.index]:
        result.append((2 * edge + (0 if graph.edges[edge][0] == start.index else 1), length))
    return result


def _goal_states(graph, goal):
    """ゴールに当たる状態のリスト (頂点ならそこへ着く状態、エッジならそのエッジの両向き)。"""
    if goal.kind == PICK_EDGE:
        return [2 * goal.index, 2 * goal.index + 1]
    return [2 * edge + (0 if graph.edges[edge][1] == goal.index else 1)
            for _neighbor, edge, _length in graph.neighbors[goal.index]]


def _result(graph, states, cost):
    """状態の列 (スタートから) を PathResult にする。"""
    vertices = [_tail(graph, states[0])] + [_head(graph, s) for s in states]
    edges = [s >> 1 for s in states]
    return PathResult(vertices, edges, sum(graph.lengths[e] for e in edges), cost)


def path_cost(graph, vertices, edges, weight, start_is_edge=False):
    """パスのコスト (テスト・比べる用)。start_is_edge なら先頭のエッジの長さは数えない。"""
    ux, uy, uz = _units(graph)
    scale = weight * turn_scale(graph)
    total = 0.0
    previous = None
    for index, edge in enumerate(edges):
        sign = 1.0 if graph.edges[edge][0] == vertices[index] else -1.0
        direction = (sign * ux[edge], sign * uy[edge], sign * uz[edge])
        if not (index == 0 and start_is_edge):
            total += graph.lengths[edge]
        if previous is not None:
            cos = sum(p * d for p, d in zip(previous, direction))
            total += scale * (1.0 - cos)
        previous = direction
    return total


def turn_shortest_path(graph, start, goal, weight):
    """曲がりの重み付きの最短パス (Python の A*)。無ければ None。"""
    if start == goal:
        return _same(graph, start)
    edges = graph.edges
    neighbors = graph.neighbors
    ux, uy, uz = _units(graph)
    scale = weight * turn_scale(graph)
    xs, ys, zs = graph.xs, graph.ys, graph.zs
    targets = graph.endpoints(goal)
    ax, ay, az = xs[targets[0]], ys[targets[0]], zs[targets[0]]
    bx, by, bz = xs[targets[-1]], ys[targets[-1]], zs[targets[-1]]
    goal_edge = goal.index if goal.kind == PICK_EDGE else None
    goal_vertex = goal.index if goal.kind == PICK_VERTEX else None
    sqrt = math.sqrt
    push, pop = heapq.heappush, heapq.heappop
    infinity = float("inf")

    best = {}
    previous = {}
    queue = []
    for state, cost in _first_states(graph, start):
        if cost < best.get(state, infinity):
            best[state] = cost
            previous[state] = None
            push(queue, (cost, cost, state))
    reached = None
    while queue:
        _estimate, so_far, state = pop(queue)
        if so_far > best[state]:
            continue
        edge = state >> 1
        head = edges[edge][0] if state & 1 else edges[edge][1]
        if head == goal_vertex or edge == goal_edge:
            reached = state
            break
        sign = -1.0 if state & 1 else 1.0
        px, py, pz = sign * ux[edge], sign * uy[edge], sign * uz[edge]
        for neighbor, next_edge, length in neighbors[head]:
            if next_edge == edge:
                continue   # 来たエッジを戻らない
            if edges[next_edge][0] == head:
                next_state, s = 2 * next_edge, 1.0
            else:
                next_state, s = 2 * next_edge + 1, -1.0
            cos = s * (px * ux[next_edge] + py * uy[next_edge] + pz * uz[next_edge])
            total = so_far + length + scale * (1.0 - cos)
            if total < best.get(next_state, infinity):
                best[next_state] = total
                previous[next_state] = state
                x, y, z = xs[neighbor], ys[neighbor], zs[neighbor]
                da = (x - ax) * (x - ax) + (y - ay) * (y - ay) + (z - az) * (z - az)
                db = (x - bx) * (x - bx) + (y - by) * (y - by) + (z - bz) * (z - bz)
                push(queue, (total + sqrt(da if da < db else db), total, next_state))
    if reached is None:
        return None
    states = [reached]
    while previous[states[-1]] is not None:
        states.append(previous[states[-1]])
    states.reverse()
    return _result(graph, states, best[reached])


class PythonTurnPathTree(object):
    """scipy が無いとき: ゴールごとに状態の A* で探して覚える。"""

    backend = "python"

    def __init__(self, graph, start, weight):
        self.graph = graph
        self.start = start
        self.weight = weight
        self._paths = {}

    def pathTo(self, goal):
        key = goal.key()
        if key not in self._paths:
            self._paths[key] = turn_shortest_path(self.graph, self.start, goal, self.weight)
        return self._paths[key]


def _transitions(graph, numpy):
    """状態のつながり (from, to, 進む長さ, 曲がりの量 1 - cos) を numpy の配列で (グラフごとに 1 回)。

    状態 p (着いた頂点 u) から、u を出ていくすべての状態 d へ (U ターン d == p ^ 1 は除く)。
    出ていく状態を「出る頂点」で並べ替えておき、p ごとに u の範囲をまとめて取り出す (ループなし)。
    """
    cached = graph.cache.get("turn_transitions")
    if cached is not None:
        return cached
    np = numpy
    count = 2 * len(graph.edges)
    pairs = np.asarray(graph.edges, dtype=np.int64).reshape(-1, 2)
    tails = np.empty(count, dtype=np.int64)
    heads = np.empty(count, dtype=np.int64)
    tails[0::2], heads[0::2] = pairs[:, 0], pairs[:, 1]
    tails[1::2], heads[1::2] = pairs[:, 1], pairs[:, 0]
    points = np.asarray(graph.points, dtype=np.float64).reshape(-1, 3)
    vectors = points[heads] - points[tails]
    lengths = np.sqrt((vectors * vectors).sum(axis=1))
    units = vectors / np.where(lengths > 0.0, lengths, 1.0)[:, None]
    order = np.argsort(tails, kind="stable")          # 出る頂点の順に並べた状態
    out_count = np.bincount(tails, minlength=len(graph.points))
    out_start = np.concatenate([[0], np.cumsum(out_count)[:-1]])
    successors = out_count[heads]                      # 状態ごとの次の候補の数
    sources = np.repeat(np.arange(count), successors)
    offsets = np.arange(len(sources)) - np.repeat(np.cumsum(successors) - successors, successors)
    targets = order[np.repeat(out_start[heads], successors) + offsets]
    keep = targets != (sources ^ 1)
    sources, targets = sources[keep], targets[keep]
    bend = np.maximum(1.0 - (units[sources] * units[targets]).sum(axis=1), 0.0)
    cached = (sources, targets, lengths[targets], bend, count)
    graph.cache["turn_transitions"] = cached
    return cached


class TurnPathTree(object):
    """scipy があるとき: 状態の疎行列で、スタートからすべての状態までを 1 回で探す。"""

    backend = "scipy"
    _NONE = -9999

    def __init__(self, graph, start, weight):
        self.graph = graph
        self.start = start
        self.weight = weight
        modules = accel.scipy_modules()
        np, sparse, csgraph = modules[0], modules[1], modules[2]
        sources, targets, steps, bend, count = _transitions(graph, np)
        costs = np.maximum(steps + weight * turn_scale(graph) * bend, _TINY)
        # 仮の始点 S (番号 count) から最初の状態へ、最初のコストの辺を張る
        first = _first_states(graph, start)
        origin = count
        rows = np.concatenate([sources, np.full(len(first), origin, dtype=np.int64)])
        cols = np.concatenate([targets, np.asarray([s for s, _c in first], dtype=np.int64)])
        values = np.concatenate([costs, np.asarray([max(c, _TINY) for _s, c in first])])
        matrix = sparse.csr_matrix((values, (rows, cols)), shape=(count + 1, count + 1))
        dist, previous = csgraph.dijkstra(matrix, directed=True, indices=origin,
                                          return_predecessors=True)
        self._dist = dist
        self._previous = previous
        self._origin = origin

    def cost(self, state):
        return float(self._dist[state])

    def pathTo(self, goal):
        if goal == self.start:
            return _same(self.graph, self.start)
        candidates = _goal_states(self.graph, goal)
        if not candidates:
            return None
        reached = min(candidates, key=self.cost)
        if math.isinf(self.cost(reached)):
            return None
        states = [reached]
        while True:
            before = int(self._previous[states[-1]])
            if before == self._origin or before == self._NONE:
                break
            states.append(before)
        states.reverse()
        # 最初の状態のコストには _TINY が入りうるので、コストは長さと曲がりから数え直さない (表示用)
        return _result(self.graph, states, self.cost(reached))


def turn_path_tree(graph, start, weight, use_scipy=None):
    """曲がりの重み付きの PathTree (use_scipy を省くと、scipy が使えれば TurnPathTree)。"""
    if use_scipy is None:
        use_scipy = accel.available()
    if use_scipy:
        return TurnPathTree(graph, start, weight)
    return PythonTurnPathTree(graph, start, weight)
