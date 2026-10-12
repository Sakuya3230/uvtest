# -*- coding: utf-8 -*-
"""
ビューのボタンの配置 (Maya に依存しない)。

    layout = panel_layout(port_width, port_height)   # {操作の ID: (左, 下, 右, 上)}
    button_at(layout, x, y)                          # 位置のボタンの ID (無ければ None)

ビューの下の中央に、操作の表 (core.actions.ACTIONS) の順で 1 段に並べる。組 (GROUPS) の間は
少し広く空ける。ビューの幅に 1 段で収まらなければ、組の切れ目で 2 段に分ける (panel_rows。
ビューを横に狭めると見切れていた)。Maya のビューの座標は左下が原点で、上が +y (ピクセル)。

置き場所は旧版で決めたもの: 左上は HUD (ポリゴン数など) と重なって読めなかった。左下は軸の表示、
下の中央のいちばん下はカメラの名前と重なるので、カメラの名前より上 (PANEL_BOTTOM) にする。
"""
from .actions import GROUPS, visible_actions

__all__ = ["panel_layout", "panel_rows", "button_at", "button_state", "PANEL_BOTTOM", "BUTTON_WIDTH",
           "BUTTON_HEIGHT", "BUTTON_COLORS", "TEXT_COLORS"]

PANEL_BOTTOM = 36     # ビューの下の辺からボタンの下の辺までの距離
BUTTON_WIDTH = 80     # 文字のまわりに余白を取る (72 では「自動:カット」が詰まって見えた)
BUTTON_HEIGHT = 24
BUTTON_GAP = 6        # ボタンの間隔 (1 段のときは同じ組の間、2 段のときはすべての間)
GROUP_GAP = 14        # 組の間隔 (1 段のときだけ)
SIDE_MARGIN = 4       # 狭いビューでも左端は見えるように
ROW_GAP = 6           # 2 段にしたときの段の間隔

# ボタンの状態 -> 表示の色 (カラーマネジメントの逆変換は tool.drawing がする)
BUTTON_COLORS = {
    "normal": (0.24, 0.24, 0.24),
    "hover": (0.36, 0.36, 0.36),
    "pressed": (0.20, 0.45, 0.70),
    "disabled": (0.18, 0.18, 0.18),
}
TEXT_COLORS = {True: (0.95, 0.95, 0.95), False: (0.50, 0.50, 0.50)}   # 押せる / 押せない


def _ordered(actions):
    """組 (GROUPS) の順に並べた操作のリスト (同じ組の中は表の順)。"""
    return [a for group in GROUPS for a in actions if a.group == group]


def _row_width(row):
    """1 段の幅。同じ組のボタンの間は BUTTON_GAP、組が変わる所は GROUP_GAP。"""
    if not row:
        return 0
    gaps = sum(GROUP_GAP if a.group != b.group else BUTTON_GAP for a, b in zip(row, row[1:]))
    return len(row) * BUTTON_WIDTH + gaps


def _grid_width(count):
    """2 段のとき (格子) の、count 個のボタンの段の幅 (間隔はすべて BUTTON_GAP)。"""
    return count * BUTTON_WIDTH + max(count - 1, 0) * BUTTON_GAP


def panel_rows(port_width, actions=None):
    """ボタンを段に分ける: [上の段, 下の段] か [1 段]。2 段までの想定。

    1 段でビューの幅 (左右の余白を除く) に収まれば 1 段。収まらなければ 2 段に分ける
    (2 段のときの幅は格子の幅 _grid_width で測る):
        1. 組の切れ目で、両方の段が収まるもののうち、長いほうの段がいちばん短いもの
        2. 無ければ、組の途中も含めて、同じ選び方
        3. それでも収まらなければ、組の切れ目で長いほうの段がいちばん短いもの (はみ出す)
    上の段が前の操作 (読む順は左から右、上から下)。
    actions を省くと、パスのモードで見えるボタン (core.actions.visible_actions)。
    """
    if actions is None:
        actions = visible_actions()
    ordered = _ordered(actions)
    available = port_width - 2 * SIDE_MARGIN
    if _row_width(ordered) <= available or len(ordered) < 2:
        return [ordered]
    group_cuts = [i for i in range(1, len(ordered)) if ordered[i].group != ordered[i - 1].group]
    all_cuts = list(range(1, len(ordered)))

    def longest(cut):
        return _grid_width(max(cut, len(ordered) - cut))

    for cuts in (group_cuts, all_cuts):
        fitting = [cut for cut in cuts if longest(cut) <= available]
        if fitting:
            cut = min(fitting, key=longest)
            return [ordered[:cut], ordered[cut:]]
    cut = min(group_cuts or all_cuts, key=longest)
    return [ordered[:cut], ordered[cut:]]


def panel_layout(port_width, port_height, actions=None):
    """ボタンの画面の矩形 {操作の ID: (左, 下, 右, 上)}。ビューの下の中央に置く。

    1 段: 組の間を GROUP_GAP、同じ組の間を BUTTON_GAP 空けて、中央に並べる。
    2 段 (幅に収まらないとき。panel_rows): **格子** に並べる。両方の段で同じ列の位置を使い
    (ボタンの左端を上下で揃える)、間隔はすべて BUTTON_GAP。段ごとに中央に揃えると、組の間隔の
    違いで上下の段がずれて不揃いに見えた。下の段は今までと同じ高さ (PANEL_BOTTOM)、上の段はその上。
    それでもはみ出すほど狭いときは、左端を SIDE_MARGIN に寄せる (左端は見える)。
    """
    rows = panel_rows(port_width, actions)
    rects = {}
    if len(rows) == 1:
        row = rows[0]
        left = max(SIDE_MARGIN, (port_width - _row_width(row)) / 2.0)
        previous = None
        for action in row:
            if previous is not None:
                left += GROUP_GAP if action.group != previous.group else BUTTON_GAP
            rects[action.id] = (left, PANEL_BOTTOM, left + BUTTON_WIDTH, PANEL_BOTTOM + BUTTON_HEIGHT)
            left += BUTTON_WIDTH
            previous = action
        return rects
    columns = max(len(row) for row in rows)
    grid_left = max(SIDE_MARGIN, (port_width - _grid_width(columns)) / 2.0)
    for level, row in enumerate(reversed(rows)):   # 下の段から
        bottom = PANEL_BOTTOM + level * (BUTTON_HEIGHT + ROW_GAP)
        for column, action in enumerate(row):
            left = grid_left + column * (BUTTON_WIDTH + BUTTON_GAP)
            rects[action.id] = (left, bottom, left + BUTTON_WIDTH, bottom + BUTTON_HEIGHT)
    return rects


def button_at(layout, x, y):
    """画面の (x, y) にあるボタンの ID。無ければ None。"""
    for action_id, (left, bottom, right, top) in layout.items():
        if left <= x <= right and bottom <= y <= top:
            return action_id
    return None


def button_state(action_id, enabled, hover, pressed):
    """ボタンの状態の名前 (BUTTON_COLORS のキー)。

    hover はマウスの下のボタン、pressed は押して、まだ離していないボタン。押したまま外へ出たら
    (hover が別のボタンか None)、押したボタンは普通の色に戻す (そこで離せばやめられる、と分かるように)。
    押している間は、ほかのボタンをホバーの色にしない。
    """
    if not enabled:
        return "disabled"
    if pressed is not None:
        return "pressed" if action_id == pressed and hover == pressed else "normal"
    if action_id == hover:
        return "hover"
    return "normal"
