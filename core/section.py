# -*- coding: utf-8 -*-
"""
輪切り: 描いた線とカメラで決まる「切る面」で、メッシュのフェースを 2 つに分け、その境目のエッジを求める
(Maya に依存しない。段階 19 の作り直し)。

    topology = SectionTopology(edges, face_counts, face_connects)   # トポロジーごとに 1 回 (押したとき)
    plane = plane_from_rays((s0, r0), (s1, r1))                     # 線の両端の視線 2 本から
    edges = section_edges(topology, points, plane, screen, stroke)   # ドラッグのたびに (速い)

仕組み:
1. 線の両端を通る視線 (始点 s・向き r) を 2 本取ると、切る面は s0・s0 + r0・s1 + r1 を通る平面
   (透視でも平行投影でも同じ式。画面では、面の上の点はすべて線の延長の上に写る)
2. 全頂点の、面からの符号付きの距離 d
3. 各フェースを、頂点の d の平均の符号で 2 つに分ける
4. 両側のフェースにはさまれたエッジ = 境目。筒を 2 つに分けた境目なので、トポロジーによらず閉じた輪になる
   (三角形・ポール・途切れたループでもよい)。境界のエッジ (フェースが 1 つ) は境目にしない
5. 画面で線の範囲 (線に投げた位置 0〜1) にあるエッジだけ残す。面は線の延長の上で胴体なども切るが、
   線の範囲の外なので外れる。裏側も同じ面で切れるので、表 / 裏は調べなくてよい

numpy があれば、2〜5 は全頂点・全フェース・全エッジの配列の計算だけ (ドラッグ中に呼ぶので)。

微調整 (段階 21): shift_plane で面を法線の向きにずらす (輪が腕に沿って動く)、tilt_plane で面を回す
(線を軸に手前 / 奥へ傾ける。今の視点からは描けない奥行きの傾き)。
縦の継ぎ目 (段階 21): 腕に沿って描くと、面は腕を縦に切り、境目は手前と奥の 2 本になる。back_half で
カメラから見て奥 (境目の中心より視線の先) のエッジだけを残す。

なめらかにする (smooth_ring。離したときに 1 回。段階 20):
境目は面に一番近いエッジを通るので、斜めの面では段差 (階段) になる。境目のまわり SMOOTH_RINGS 段の頂点だけを
使い、「エッジの長さ + SMOOTH_WEIGHT x 面からの距離」が最小の道で一周を引き直す。一周させるため、画面で線の
いちばん手前 / 奥に写る境目の頂点 A・B を決め、A -> B の道を 1 本探し、その途中の頂点を外してもう 1 本探す
(筒の手前側と奥側)。2 本を合わせると閉じた輪になる。範囲が狭いので Python の Dijkstra で足りる。
エッジとフェースの対応は SectionTopology が 1 回だけ作る (面の角の組から、エッジの鍵を searchsorted)。
"""
import math

from . import accel

__all__ = ["SectionTopology", "plane_from_rays", "section_edges", "smooth_ring", "is_closed_ring",
           "shift_plane", "tilt_plane", "back_half", "TILT_DEGREES",
           "SMOOTH_RINGS", "SMOOTH_WEIGHT"]

SMOOTH_RINGS = 2      # なめらかにするとき、境目から何段まで道に使うか
SMOOTH_WEIGHT = 4.0   # 面からの距離の重み (エッジの長さに足す。大きいほど面に沿う)
TILT_DEGREES = 3.0    # 傾けるときの 1 目盛り (段階 21)


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def plane_from_rays(ray0, ray1):
    """視線 2 本 ((始点, 向き), (始点, 向き)) を含む平面 (点, 単位の法線)。決まらなければ None。"""
    (s0, r0), (s1, r1) = ray0, ray1
    a = tuple(r0)
    b = _sub((s1[0] + r1[0], s1[1] + r1[1], s1[2] + r1[2]), s0)
    n = _cross(a, b)
    length = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
    if length < 1e-12:
        return None   # 線が短すぎる・視線と平行
    return tuple(s0), (n[0] / length, n[1] / length, n[2] / length)


class SectionTopology(object):
    """エッジの両端と、エッジの両側のフェース (トポロジーが同じ間は使い回す)。

    edges は [(a, b)] (MeshGraph.edges)、face_counts はフェースごとの頂点の数、face_connects は
    フェースごとの頂点を並べたもの (MFnMesh.getVertices)。
    """

    def __init__(self, edges, face_counts, face_connects):
        self.edges = edges
        self.counts = list(face_counts)
        self.connects = list(face_connects)
        self.face_count = len(self.counts)
        self._np = None
        modules = accel.scipy_modules()
        if modules is not None and self.face_count:
            self._build_numpy(modules[0])
        else:
            self._build_python()

    def _build_numpy(self, np):
        self._np = np
        counts = np.asarray(self.counts, dtype=np.int64)
        connects = np.asarray(self.connects, dtype=np.int64)
        starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
        corner_face = np.repeat(np.arange(len(counts)), counts)
        following = np.arange(len(connects)) + 1
        following[starts + counts - 1] = starts   # 最後の角の次は最初の角
        a, b = connects, connects[following]
        vertex_count = int(max(connects.max(), np.asarray(self.edges).max()) + 1)
        keys = np.minimum(a, b) * vertex_count + np.maximum(a, b)
        ends = np.asarray(self.edges, dtype=np.int64).reshape(-1, 2)
        edge_keys = ends.min(axis=1) * vertex_count + ends.max(axis=1)
        order = np.argsort(edge_keys, kind="stable")
        position = np.clip(np.searchsorted(edge_keys[order], keys), 0, len(order) - 1)
        corner_edge = order[position]
        # エッジごとに、最初に出てくるフェースと 2 つ目のフェース (無ければ -1)
        sort = np.argsort(corner_edge, kind="stable")
        edge_sorted, face_sorted = corner_edge[sort], corner_face[sort]
        first = np.ones(len(edge_sorted), dtype=bool)
        first[1:] = edge_sorted[1:] != edge_sorted[:-1]
        f0 = np.full(len(ends), -1, dtype=np.int64)
        f1 = np.full(len(ends), -1, dtype=np.int64)
        f0[edge_sorted[first]] = face_sorted[first]
        f1[edge_sorted[~first]] = face_sorted[~first]
        self.arrays = {"ends": ends, "connects": connects, "starts": starts, "counts": counts,
                       "f0": f0, "f1": f1}

    def _build_python(self):
        lookup = {}
        for e, (a, b) in enumerate(self.edges):
            lookup[(a, b) if a < b else (b, a)] = e
        faces = [[] for _ in self.edges]
        self.face_vertices = []
        index = 0
        for face, count in enumerate(self.counts):
            vertices = self.connects[index:index + count]
            index += count
            self.face_vertices.append(vertices)
            for k in range(count):
                a, b = vertices[k], vertices[(k + 1) % count]
                edge = lookup.get((a, b) if a < b else (b, a))
                if edge is not None:
                    faces[edge].append(face)
        self.edge_faces = faces


def section_edges(topology, points, plane, screen, stroke):
    """切る面で分けたフェースの境目のエッジのうち、画面で線の範囲にあるもの (エッジの番号のリスト)。

    points は頂点のワールドの位置、screen は頂点の画面の位置 ((x, y) か None)、stroke は core.ring.Stroke。
    """
    if plane is None or stroke.length <= 0:
        return []
    if topology._np is not None:
        return _section_numpy(topology, points, plane, screen, stroke)
    return _section_python(topology, points, plane, screen, stroke)


def _screen_array(np, screen):
    cached = getattr(screen, "_section_array", None)
    if cached is not None:
        return cached
    valid = np.fromiter((p is not None for p in screen), dtype=bool, count=len(screen))
    xy = np.asarray([p if p is not None else (0.0, 0.0) for p in screen], dtype=np.float64)
    return valid, xy


def _section_numpy(topology, points, plane, screen, stroke):
    np = topology._np
    arrays = topology.arrays
    origin, normal = plane
    coords = points if isinstance(points, np.ndarray) else np.asarray(points, dtype=np.float64)
    distance = (coords - np.asarray(origin)).dot(np.asarray(normal))
    sums = np.add.reduceat(distance[arrays["connects"]], arrays["starts"])
    side = sums >= 0.0
    f0, f1 = arrays["f0"], arrays["f1"]
    inner = (f0 >= 0) & (f1 >= 0)
    boundary = np.zeros(len(f0), dtype=bool)
    boundary[inner] = side[f0[inner]] != side[f1[inner]]
    ids = np.nonzero(boundary)[0]
    if not len(ids):
        return []
    valid, xy = screen if isinstance(screen, tuple) else _screen_array(np, screen)
    ends = arrays["ends"][ids]
    ok = valid[ends[:, 0]] & valid[ends[:, 1]]
    ids, ends = ids[ok], ends[ok]
    mid = (xy[ends[:, 0]] + xy[ends[:, 1]]) * 0.5
    dx, dy = stroke.direction
    t = ((mid[:, 0] - stroke.start[0]) * dx + (mid[:, 1] - stroke.start[1]) * dy) / stroke.length
    return ids[(t >= 0.0) & (t <= 1.0)].tolist()


def _section_python(topology, points, plane, screen, stroke):
    origin, normal = plane
    distance = [(p[0] - origin[0]) * normal[0] + (p[1] - origin[1]) * normal[1]
                + (p[2] - origin[2]) * normal[2] for p in points]
    side = [sum(distance[v] for v in vertices) >= 0.0 for vertices in topology.face_vertices]
    result = []
    for edge, faces in enumerate(topology.edge_faces):
        if len(faces) < 2 or side[faces[0]] == side[faces[1]]:
            continue
        a, b = topology.edges[edge]
        pa, pb = screen[a], screen[b]
        if pa is None or pb is None:
            continue
        t, _distance = stroke.project(((pa[0] + pb[0]) * 0.5, (pa[1] + pb[1]) * 0.5))
        if 0.0 <= t <= 1.0:
            result.append(edge)
    return result



def is_closed_ring(edges, chosen):
    """chosen (エッジの番号) が閉じた輪の集まりか (どの頂点にもちょうど 2 本がつながる)。"""
    degree = {}
    for edge in chosen:
        for vertex in edges[edge]:
            degree[vertex] = degree.get(vertex, 0) + 1
    return bool(degree) and all(count == 2 for count in degree.values())


def _dijkstra(neighbors, allowed, banned_edges, cost, start, goal):
    """allowed の頂点だけを通る start -> goal の最小コストの道 (エッジのリスト)。無ければ None。"""
    import heapq
    best = {start: 0.0}
    previous = {start: None}
    queue = [(0.0, start)]
    while queue:
        so_far, vertex = heapq.heappop(queue)
        if vertex == goal:
            break
        if so_far > best[vertex]:
            continue
        for neighbor, edge, _length in neighbors[vertex]:
            if neighbor not in allowed or edge in banned_edges:
                continue
            total = so_far + cost(edge)
            if total < best.get(neighbor, float("inf")):
                best[neighbor] = total
                previous[neighbor] = (vertex, edge)
                heapq.heappush(queue, (total, neighbor))
    if goal not in previous:
        return None
    path = []
    vertex = goal
    while previous[vertex] is not None:
        vertex, edge = previous[vertex]
        path.append(edge)
    path.reverse()
    return path


def smooth_ring(graph, plane, ring, screen, stroke, rings=SMOOTH_RINGS, weight=SMOOTH_WEIGHT):
    """境目 ring (エッジ) を、まわりの数段の中で、面に沿うなだらかな一周に引き直す。できなければ None。

    graph は core.graph.MeshGraph (頂点の位置・隣接)、screen は頂点の画面の位置 ((x, y) か None)。
    輪が 2 つ以上 (線が 2 本の筒にかかった) のときは引き直さない (None)。
    """
    if not ring or plane is None:
        return None
    origin, normal = plane
    points, edges, neighbors = graph.points, graph.edges, graph.neighbors

    def distance(vertex):
        p = points[vertex]
        return abs((p[0] - origin[0]) * normal[0] + (p[1] - origin[1]) * normal[1]
                   + (p[2] - origin[2]) * normal[2])

    ring_vertices = set(v for e in ring for v in edges[e])
    band = set(ring_vertices)
    frontier = set(ring_vertices)
    for _ in range(rings):
        grown = set()
        for vertex in frontier:
            for neighbor, _edge, _length in neighbors[vertex]:
                if neighbor not in band:
                    grown.add(neighbor)
        band |= grown
        frontier = grown
    # 手前 / 奥: 画面で線のいちばん端に写る境目の頂点
    placed = [(stroke.project(screen[v])[0], v) for v in ring_vertices if screen[v] is not None]
    if len(placed) < 2:
        return None
    placed.sort()
    a, b = placed[0][1], placed[-1][1]
    if a == b:
        return None
    cache = {}

    def cost(edge):
        value = cache.get(edge)
        if value is None:
            u, v = edges[edge]
            value = cache[edge] = graph.lengths[edge] + weight * (distance(u) + distance(v)) * 0.5
        return value

    first = _dijkstra(neighbors, band, set(), cost, a, b)
    if not first:
        return None
    inner = set(v for e in first for v in edges[e]) - {a, b}
    second = _dijkstra(neighbors, band - inner, set(first), cost, a, b)
    if not second:
        return None
    result = first + second
    if not is_closed_ring(edges, result):
        return None
    return result



def _normalize(v):
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return (v[0] / length, v[1] / length, v[2] / length) if length > 1e-12 else None


def shift_plane(plane, distance):
    """面を法線の向きに distance だけずらす (段階 21)。"""
    origin, normal = plane
    return (tuple(origin[k] + normal[k] * distance for k in range(3)), normal)


def tilt_plane(plane, view_direction, degrees, center):
    """面を、線 (面の中で視線に垂直な向き) を軸に degrees 度回す。回す中心は center (段階 21)。

    軸 = 法線 x 視線。視線の向きの成分が法線に入るので、輪が手前 / 奥へ傾く (画面の上の線の向きは同じ)。
    """
    origin, normal = plane
    axis = _normalize(_cross(normal, view_direction))
    if axis is None:
        return plane
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    dot = sum(axis[k] * normal[k] for k in range(3))
    cross = _cross(axis, normal)
    rotated = tuple(normal[k] * c + cross[k] * s + axis[k] * dot * (1.0 - c) for k in range(3))
    return (tuple(center), _normalize(rotated))


def back_half(edges, points, chosen, view_direction):
    """chosen (エッジ) のうち、カメラから見て奥のもの (中点が、境目の頂点の中心より視線の先)。"""
    vertices = set(v for e in chosen for v in edges[e])
    if not vertices:
        return []
    center = tuple(sum(points[v][k] for v in vertices) / len(vertices) for k in range(3))
    result = []
    for edge in chosen:
        a, b = edges[edge]
        mid = tuple((points[a][k] + points[b][k]) * 0.5 - center[k] for k in range(3))
        if sum(mid[k] * view_direction[k] for k in range(3)) > 0.0:
            result.append(edge)
    return result
