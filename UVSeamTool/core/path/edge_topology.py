"""
エッジのまわりのつながり (頂点 -> エッジ・エッジ -> 面・面 -> エッジ) とエッジのループ。Maya には触らない。
"""

from __future__ import annotations

import math

_GRID_VALENCE       = 4                     # 四角形の格子の頂点の辺の数 (面を共有しない辺がちょうど 1 本)
_TRIANGLE_VALENCE   = 6                     # 三角形を越えて進むのは、辺の数がこれ以下の頂点だけ (極などのポールは越えない)
_STRAIGHT_ANGLE     = math.radians(45.0)    # 三角形を越えるとき、この角度より曲がる辺には進まない


class EdgeTopology:
    """メッシュのエッジのまわりのつながり。エッジのループを求める。

    edges はエッジ (M, 2)、counts / connects は面ごとの頂点の数と並び (MFnMesh.getVertices)。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, edges, counts, connects):
        edge_list    = [tuple(edge) for edge in edges.tolist()]
        edge_of      = {_key(a, b): index for index, (a, b) in enumerate(edge_list)}
        vertex_edges = {}
        for index, (a, b) in enumerate(edge_list):
            vertex_edges.setdefault(a, []).append(index)
            vertex_edges.setdefault(b, []).append(index)

        face_edges = []
        face_sizes = []
        edge_faces = [[] for _ in edge_list]
        start      = 0
        connects   = connects.tolist()
        for face, count in enumerate(counts.tolist()):
            corners = connects[start:start + count]
            ids     = [edge_of[_key(corners[i], corners[(i + 1) % count])] for i in range(count)]
            for edge in ids:
                edge_faces[edge].append(face)
            face_edges.append(ids)
            face_sizes.append(count)
            start += count

        self._edges         = edge_list
        self._vertex_edges  = vertex_edges
        self._edge_faces    = edge_faces
        self._face_edges    = face_edges
        self._face_sizes    = face_sizes

    # -- 公開メソッド ---------------------------------------------------------
    def edgeVertices(self, edge):
        """エッジの両端の頂点 (a, b)。"""
        return self._edges[edge]

    def faceEdges(self, face):
        """面のエッジの番号のリスト (面の頂点の順)。"""
        return list(self._face_edges[face])

    def edgeFaces(self, edge):
        """エッジに接する面の番号のリスト (縁のエッジは 1 つ)。"""
        return list(self._edge_faces[edge])

    def edgeLoop(self, edge, positions):
        """edge を通るエッジのループ (エッジの番号のリスト。順は問わない)。positions は頂点の位置 (N, 3)。

        進んできた先の頂点で、次のエッジを決める (_next_in_loop):
          今のエッジが縁               -> 縁に沿って次の縁のエッジ (Maya のダブルクリックと同じ)
          辺の数が 4 (四角形の格子)    -> 面を共有しない、ちょうど 1 本の辺
          まわりに三角形があり辺が 6 以下 -> 面を共有しない辺のうち、いちばんまっすぐ続く辺 (45 度より曲がるなら止まる)
          それ以外 (ポールなど)         -> 止まる
        両方向に進み、出発のエッジに戻ったら一周。
        """
        loop = {edge}
        for end in (0, 1):
            current = edge
            vertex  = self._edges[edge][end]
            while True:
                following = self._next_in_loop(current, vertex, positions)
                if following is None or following in loop:
                    break

                loop.add(following)
                a, b    = self._edges[following]
                vertex  = b if a == vertex else a
                current = following

        return sorted(loop)

    # -- 非公開メソッド -------------------------------------------------------
    def _next_in_loop(self, edge, vertex, positions):
        # vertex で edge の続きになるエッジ (無ければ None)
        around = self._vertex_edges.get(vertex, [])
        if self._is_border(edge):
            borders = [other for other in around if other != edge and self._is_border(other)]
            return borders[0] if len(borders) == 1 else None

        faces      = set(self._edge_faces[edge])
        candidates = [other for other in around
                      if other != edge and not self._is_border(other) and not (set(self._edge_faces[other]) & faces)]
        if len(around) == _GRID_VALENCE and not self._touches_triangle(around):
            return candidates[0] if len(candidates) == 1 else None

        if len(around) > _TRIANGLE_VALENCE or not self._touches_triangle(around):
            return None

        return self._straightest(edge, vertex, candidates, positions)

    def _straightest(self, edge, vertex, candidates, positions):
        # candidates のうち、edge からいちばんまっすぐ続く辺 (_STRAIGHT_ANGLE より曲がるなら None)
        previous  = self._other_end(edge, vertex)
        incoming  = _direction(positions[previous], positions[vertex])
        best      = None
        best_turn = _STRAIGHT_ANGLE
        for other in candidates:
            outgoing = _direction(positions[vertex], positions[self._other_end(other, vertex)])
            turn     = math.acos(max(-1.0, min(1.0, sum(i * o for i, o in zip(incoming, outgoing)))))
            if turn <= best_turn:
                best, best_turn = other, turn

        return best

    def _touches_triangle(self, around):
        # 頂点のまわりの辺 (around) の面に三角形があるか
        return any(self._face_sizes[face] == 3 for edge in around for face in self._edge_faces[edge])

    def _is_border(self, edge):
        return len(self._edge_faces[edge]) == 1

    def _other_end(self, edge, vertex):
        a, b = self._edges[edge]

        return b if a == vertex else a


def _direction(start, end):
    # start -> end の向き (長さ 1)。長さ 0 なら (0, 0, 0)
    vector = [float(e) - float(s) for s, e in zip(start, end)]
    length = math.sqrt(sum(v * v for v in vector))

    return [v / length for v in vector] if length > 0.0 else [0.0, 0.0, 0.0]


def _key(a, b):
    return (a, b) if a < b else (b, a)
