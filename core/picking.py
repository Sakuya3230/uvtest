# -*- coding: utf-8 -*-
"""
マウスの下のもの (Maya に依存しない)。

段階 3: FaceHit (レイが当たった面)。座標は (x, y, z) のタプル (Maya の型を持たない。
        scene/mesh.py の MeshModel.hit が作る)。
段階 4: 当たった面の角 / 辺から、画面でマウスに最も近い頂点 / エッジを選ぶ (pick_component)。

    pick = pick_component(hit, model.face_edges(hit.face), PICK_EDGE, (x, y), project)

project(点) -> (x, y) はワールドの点を画面のピクセルへ投影する関数 (Maya では
M3dView.worldToView。テストでは決まった投影を渡す)。画面で比べるのは、斜めから見た面でも
見た目どおりに近いものを選ぶため (ワールドの距離だと、手前に傾いた辺が遠く見えても選ばれる)。
"""

__all__ = ["PICK_VERTEX", "PICK_EDGE", "FaceHit", "Pick", "segment_distance", "pick_component"]

PICK_VERTEX = "vertex"   # 頂点を拾う (設定 pickMode の選択肢と同じ名前)
PICK_EDGE = "edge"       # エッジを拾う


class FaceHit(object):
    """レイが当たった面。"""

    def __init__(self, face, point, vertices, corners, front):
        self.face = face            # 面の番号
        self.point = point          # 交点 (ワールド。タプル)
        self.vertices = vertices    # 面の頂点の番号 (角の順)
        self.corners = corners      # 面の角の位置 (ワールド。タプルのリスト。vertices と同じ順)
        self.front = front          # 表の面か (法線がレイと向き合う)

    def key(self):
        """表示を描き直すかを決めるための目印 (面と表裏)。"""
        return (self.face, self.front)

    def __repr__(self):
        return "FaceHit(face={}, front={})".format(self.face, self.front)


class Pick(object):
    """拾った頂点かエッジ。"""

    def __init__(self, kind, index, points, hit):
        self.kind = kind        # PICK_VERTEX / PICK_EDGE
        self.index = index      # 頂点かエッジの番号
        self.points = points    # 頂点なら [位置]、エッジなら [端 0, 端 1] (ワールド。タプル)
        self.hit = hit          # 拾った面 (FaceHit)

    def key(self):
        """表示を描き直すかを決めるための目印 (種類と番号)。"""
        return (self.kind, self.index)

    def label(self):
        """スクリプトエディタ・ビューに出す名前 (vtx[3] / e[12])。"""
        return "{}[{}]".format("vtx" if self.kind == PICK_VERTEX else "e", self.index)

    def __repr__(self):
        return "Pick({})".format(self.label())


def segment_distance(p, a, b):
    """画面の点 p と線分 ab の距離 (どれも (x, y))。

    線分の上で p に最も近い点 (a + t (b - a)、t は 0〜1 に収める) までの距離。
    """
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 < 1e-12 else ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length2
    t = min(1.0, max(0.0, t))
    x, y = a[0] + dx * t - p[0], a[1] + dy * t - p[1]
    return (x * x + y * y) ** 0.5


def pick_component(hit, face_edges, mode, mouse, project):
    """面 hit の角か辺のうち、画面でマウスに最も近いもの (Pick)。

    face_edges は面の辺 [(エッジの番号, 頂点 0, 頂点 1)] (頂点のモードでは使わない)。
    辺の両端の位置は hit.vertices / hit.corners から引く (面の頂点なので必ずある)。
    """
    positions = dict(zip(hit.vertices, hit.corners))
    if mode == PICK_VERTEX:
        best = None
        for vertex, point in zip(hit.vertices, hit.corners):
            x, y = project(point)
            distance = ((x - mouse[0]) ** 2 + (y - mouse[1]) ** 2) ** 0.5
            if best is None or distance < best[0]:
                best = (distance, vertex, point)
        return Pick(PICK_VERTEX, best[1], [best[2]], hit)
    best = None
    for edge, v0, v1 in face_edges:
        p0, p1 = positions[v0], positions[v1]
        distance = segment_distance(mouse, project(p0), project(p1))
        if best is None or distance < best[0]:
            best = (distance, edge, p0, p1)
    return Pick(PICK_EDGE, best[1], [best[2], best[3]], hit)
