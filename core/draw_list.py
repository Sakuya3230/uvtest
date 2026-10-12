# -*- coding: utf-8 -*-
"""
描画の一覧 (Maya に依存しない)。「何をどの役割で描くか」だけを持つ。

    items = DrawList()
    items.polygon(ROLE_FACE_FILL, corners)          # 塗り
    items.lines(ROLE_PATH, [(p0, p1), (p1, p2)])    # 線分の集まり
    items.point(ROLE_PICK, p)                       # 点
    items.text(ROLE_LABEL, p, "e[12]")              # 文字

「どう描くか」(色・太さ・カメラへ寄せる量) は役割ごとに THEME で決める。MUIDrawManager を
呼ぶのは tool/drawing.py の render だけ。こうすると:
- 何を描くかを pytest で確かめられる (マウスやビューが無くても)
- 色や太さを変えたいときは THEME の 1 行を直すだけでよい
- 同じ役割の線は render がまとめて 1 回で描く (パスの何百本の線も 1 回の呼び出し)

点は (x, y, z) のタプル (ワールド)。
"""
from .geometry import fan_triangles, midpoint
from .picking import PICK_VERTEX

__all__ = ["Style", "THEME", "DrawItem", "DrawList", "hover_items", "path_items",
           "waypoint_items", "endpoint_points", "LINES", "LOOP", "TRIANGLES", "POINT", "TEXT",
           "ROLE_FACE_FILL", "ROLE_FACE_EDGE", "ROLE_PICK", "ROLE_PATH", "ROLE_START", "ROLE_LABEL",
           "ROLE_CONFIRMED", "ROLE_CUT", "ROLE_SEW", "ROLE_SEGMENT_END", "segment_items",
           "COLOR_ROLES", "theme_colors", "loop_items", "loop_label", "ROLE_MIRROR",
           "mirror_items", "ring_items",
           "SEGMENT_ROLES"]

# 項目の種類
LINES = "lines"          # 線分の集まり (2 点ずつ)
LOOP = "loop"            # 閉じた折れ線
TRIANGLES = "triangles"  # 三角形の集まり (3 点ずつ)
POINT = "point"          # 点
TEXT = "text"            # 文字

# 役割 (何を表すか)
ROLE_FACE_FILL = "faceFill"    # マウスの下の面の塗り
ROLE_FACE_EDGE = "faceEdge"    # マウスの下の面の縁
ROLE_PICK = "pick"             # 拾った頂点 / エッジ (エンドの候補)
ROLE_PATH = "path"             # パスのプレビュー
ROLE_START = "start"           # スタート
ROLE_LABEL = "label"           # 番号などの文字
ROLE_CONFIRMED = "confirmed"   # 確定した区間 (段階 8。段階 9 からは、まだ実行していない区間)
ROLE_CUT = "cut"               # カットした区間 (段階 9)
ROLE_SEW = "sew"               # 縫合した区間 (段階 9)
ROLE_SEGMENT_END = "segmentEnd"   # 確定した区間の端点の印
ROLE_MIRROR = "mirror"         # 反対側 (プレビュー・スタート・拾ったもの。段階 17)


class Style(object):
    """役割の見た目。"""

    def __init__(self, color, alpha=1.0, width=1.0, size=1.0, layer=1.0):
        self.color = color    # 表示の色 (r, g, b)。カラーマネジメントの変換は render がする
        self.alpha = alpha    # 不透明度
        self.width = width    # 線の太さ (ピクセル)
        self.size = size      # 点の大きさ (ピクセル)
        self.layer = layer    # カメラへ寄せる度合い (大きいほど手前。面にちらつかず重ねるため)


# 役割 -> 見た目。下の役割ほど手前に (layer を大きく) する
THEME = {
    ROLE_FACE_FILL: Style((0.35, 0.95, 0.45), alpha=0.15, layer=1.0),
    ROLE_FACE_EDGE: Style((0.35, 0.95, 0.45), width=1.0, layer=1.0),
    # 未実行の区間はマゼンタ。水色はエッジの選択モードのワイヤーフレームと同じ系統で見分けにくかった
    # (GUI で確認)。ほかの役割 (黄・橙・緑・赤) とも、Maya の選択の色 (橙) とも重ならない。
    # 暗い縁取りも試したが、エッジ 1 本ずつの線分なので頂点ごとに継ぎ目が見えて見苦しく、やめた
    ROLE_CONFIRMED: Style((1.00, 0.30, 0.85), width=3.0, layer=1.2),
    ROLE_CUT: Style((1.00, 0.30, 0.30), width=3.0, layer=1.2),
    ROLE_SEW: Style((0.40, 0.95, 0.40), width=3.0, layer=1.2),
    ROLE_SEGMENT_END: Style((1.00, 0.30, 0.85), size=8.0, layer=1.2),
    ROLE_PATH: Style((1.00, 0.85, 0.20), width=4.0, layer=1.5),
    # 反対側はプレビューの色をうすく (くすんだ色)。どちらが自分の操作しているほうか分かるように
    ROLE_MIRROR: Style((1.00, 0.85, 0.20), alpha=0.45, width=3.0, size=9.0, layer=1.5),
    ROLE_START: Style((0.25, 1.00, 0.35), width=5.0, size=12.0, layer=2.0),
    ROLE_PICK: Style((1.00, 0.60, 0.15), width=5.0, size=12.0, layer=2.0),
    ROLE_LABEL: Style((0.95, 0.95, 0.95), layer=2.0),
}


# 色の設定 (core.settings の COLOR) -> その色で描く役割
COLOR_ROLES = {
    "faceColor": (ROLE_FACE_FILL, ROLE_FACE_EDGE),
    "pickColor": (ROLE_PICK,),
    "startColor": (ROLE_START,),
    "pathColor": (ROLE_PATH, ROLE_MIRROR),
    "pendingColor": (ROLE_CONFIRMED, ROLE_SEGMENT_END),
    "cutColor": (ROLE_CUT,),
    "sewColor": (ROLE_SEW,),
}


def theme_colors(values):
    """設定の値 (Settings.values()) から {役割: 色} (THEME の色を上書きするもの)。"""
    colors = {}
    for key, roles in COLOR_ROLES.items():
        if key in values:
            for role in roles:
                colors[role] = tuple(values[key])
    return colors


# 区間の状態 (PathSegment.operation) -> 役割 (段階 9)。未実行 / カット / 縫合
SEGMENT_ROLES = {None: ROLE_CONFIRMED, "cut": ROLE_CUT, "sew": ROLE_SEW}


class DrawItem(object):
    """描くもの 1 つ。"""

    def __init__(self, kind, role, points, text=""):
        self.kind = kind        # LINES / LOOP / TRIANGLES / POINT / TEXT
        self.role = role        # THEME のキー
        self.points = points    # 点のリスト
        self.text = text        # TEXT の文字

    def __repr__(self):
        return "DrawItem({}, {}, {} 点{})".format(self.kind, self.role, len(self.points),
                                                 ", " + self.text if self.text else "")


class DrawList(object):
    """描くものの一覧 (描く順。後から足したものほど上に描かれる)。"""

    def __init__(self):
        self.items = []

    def lines(self, role, segments):
        """線分の集まり [(p0, p1), ...]。"""
        points = [p for segment in segments for p in segment]
        if points:
            self.items.append(DrawItem(LINES, role, points))

    def loop(self, role, points):
        if len(points) >= 2:
            self.items.append(DrawItem(LOOP, role, list(points)))

    def polygon(self, role, corners):
        """多角形の塗り (扇形に三角形へ分ける。凸の多角形なら正しく塗れる)。"""
        if len(corners) >= 3:
            self.items.append(DrawItem(TRIANGLES, role,
                                       [corners[i] for i in fan_triangles(len(corners))]))

    def point(self, role, point):
        self.items.append(DrawItem(POINT, role, [point]))

    def text(self, role, point, text):
        self.items.append(DrawItem(TEXT, role, [point], text))

    def extend(self, other):
        self.items.extend(other.items)
        return self

    def roles(self):
        """含まれる役割 (描く順。重複なし)。テスト用。"""
        seen = []
        for item in self.items:
            if item.role not in seen:
                seen.append(item.role)
        return seen


def waypoint_items(points, role, label=""):
    """端点 (頂点なら点、エッジなら太い線) の一覧。points は頂点なら [位置]、エッジなら [端 0, 端 1]。"""
    items = DrawList()
    if len(points) == 1:
        items.point(role, points[0])
        anchor = points[0]
    else:
        items.lines(role, [(points[0], points[1])])
        anchor = midpoint(points[0], points[1])
    if label:
        items.text(ROLE_LABEL, anchor, "  " + label)
    return items


def hover_items(pick, label=""):
    """マウスの下の面 (うすく) と、拾った頂点 / エッジの一覧。label を省けば番号 (vtx[3] など)。"""
    items = DrawList()
    if pick is None:
        return items
    corners = pick.hit.corners
    items.polygon(ROLE_FACE_FILL, corners)
    items.loop(ROLE_FACE_EDGE, corners)
    return items.extend(waypoint_items(pick.points, ROLE_PICK, label or pick.label()))


def loop_label(count):
    """ループのプレビューの文字 (段階 16)。"""
    return "ループ {} 本".format(count)


def loop_items(pick, segments, label=""):
    """選択のモードのホバー (段階 16): マウスの下の面・ループのプレビュー・拾ったエッジ。

    segments はループのエッジの [(端 0, 端 1)]。パスのプレビューと同じ役割 (ROLE_PATH。色は設定の
    「プレビュー」) で描く。ダブルクリックで選ばれるものを前もって見せる。
    """
    items = DrawList()
    if pick is None:
        return items
    items.lines(ROLE_PATH, segments)
    return items.extend(hover_items(pick, label or loop_label(len(segments))))


def mirror_items(graph, edges=(), waypoints=()):
    """反対側の、うすい線 (エッジ) と端点 (段階 17)。edges / waypoints は反対側の番号のもの。"""
    items = DrawList()
    points = graph.points
    if edges:
        items.lines(ROLE_MIRROR, [(points[a], points[b]) for a, b in (graph.edges[e] for e in edges)])
    for waypoint in waypoints:
        where = endpoint_points(graph, waypoint)
        if len(where) == 1:
            items.point(ROLE_MIRROR, where[0])
        else:
            items.lines(ROLE_MIRROR, [(where[0], where[1])])
    return items


def ring_items(graph, edges, label=""):
    """輪切りのプレビュー (段階 19): ループの線 (プレビューの色) と「輪切り N 本」。"""
    items = DrawList()
    if not edges:
        return items
    points = graph.points
    items.lines(ROLE_PATH, [(points[a], points[b]) for a, b in (graph.edges[e] for e in edges)])
    a, b = graph.edges[edges[0]]
    items.text(ROLE_LABEL, midpoint(points[a], points[b]), "  " + (label or "輪切り {} 本".format(len(edges))))
    return items


def path_items(graph, path, role=ROLE_PATH):
    """パス (core.path.PathResult) のエッジの線の一覧 (1 つの LINES にまとめる)。"""
    items = DrawList()
    if path is not None and path.edges:
        points = graph.points
        items.lines(role, [(points[a], points[b]) for a, b in (graph.edges[e] for e in path.edges)])
    return items


def endpoint_points(graph, waypoint):
    """端点 (core.path.Waypoint) の位置 (頂点なら [位置]、エッジなら [端 0, 端 1])。"""
    if waypoint.kind == PICK_VERTEX:
        return [graph.points[waypoint.index]]
    a, b = graph.edges[waypoint.index]
    return [graph.points[a], graph.points[b]]


def segment_items(graph, segments):
    """確定した区間 (core.session.PathSegment) の線と、区間の両端の印 (段階 8)。

    区間は確定した順に描く (後の区間ほど上)。色は状態ごと (SEGMENT_ROLES: 未実行 マゼンタ /
    カット 赤 / 縫合 緑)。端点の印はエッジなら真ん中。Esc で鎖を切ったあとは区間がつながっていないので、区間ごとの
    両端に付ける (同じ端点は 1 つ)。
    """
    items = DrawList()
    points = graph.points
    for segment in segments:
        role = SEGMENT_ROLES[getattr(segment, "operation", None)]
        items.lines(role, [(points[a], points[b])
                                     for a, b in (graph.edges[e] for e in segment.allEdges())])
    ends = []
    for segment in segments:
        for waypoint in (segment.start, segment.end):
            if waypoint not in ends:
                ends.append(waypoint)
    for waypoint in ends:
        where = endpoint_points(graph, waypoint)
        items.point(ROLE_SEGMENT_END, where[0] if len(where) == 1 else midpoint(where[0], where[1]))
    return items
