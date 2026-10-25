"""
モードとボタンの操作の名前。
"""

from ..ui.view_panel import SEPARATOR
from .uv_apply import CUT, SEW

MODE_CREATE = "create"
MODE_EDIT   = "edit"
MODE_SELECT = "select"
MODES       = (MODE_CREATE, MODE_EDIT, MODE_SELECT)   # Tab で切り替える順

TOGGLE_MODE     = "toggleMode"
LOOP            = "loop"            # ループの事前ハイライトの切り替え (選択のモードの補助。オンにすると選択のモードになる)
SYMMETRY        = "symmetry"        # ツールの対称の切り替え (設定 symmetry。Maya の対称がオンなら、そちらが優先される)
AUTO            = "auto"            # 自動の切り替え (設定 autoApply。作成のモードで点を足すたびにカット / 縫合)
AUTO_OPERATION  = "autoOperation"   # 自動のときの操作の切り替え (設定 autoOperation。カット <-> 縫合)
DELETE_ALL      = "deleteAll"       # 対象のメッシュのガイドをすべて消す (確認しない。1 回の Undo)
DELETE_ON_COMPLETE = "deleteOnComplete"   # 確定後にガイドを削除する切り替え (設定 deleteGuideOnComplete。マーキングメニューから)
SHOW_PANEL      = "showPanel"       # ビューのパネルの表示の切り替え (設定 showPanel。マーキングメニューから)
SPLIT           = "split"           # 選んだ点でガイドを切り離す (編集のモード。マーキングメニューから)
JOIN            = "join"            # 選んだ 2 本をつなぐ・1 本を閉じる (編集のモード。マーキングメニューから)

# 設定を 1 つの値にする操作 (マーキングメニューから)。ID -> (設定のキー, 値, 表示名)
SET_SETTINGS = {
    "mirrorWorld":  ("mirrorSpace",     "world",    "ワールド"),
    "mirrorObject": ("mirrorSpace",     "object",   "オブジェクト"),
    "mirrorX":      ("mirrorAxis",      "x",        "X 軸"),
    "mirrorY":      ("mirrorAxis",      "y",        "Y 軸"),
    "mirrorZ":      ("mirrorAxis",      "z",        "Z 軸"),
    "autoCut":      ("autoOperation",   "cut",      "自動カット"),
    "autoSew":      ("autoOperation",   "sew",      "自動縫合"),
}

# ビューのパネルのボタン (ID, 表示名, 切り替えか)。並べる順。アイコンは ID と同じ名前 (ui.icons)。SEPARATOR は区切り線
PANEL_ACTIONS = (
    (MODE_CREATE,        "作成",         True),
    (MODE_EDIT,          "編集",         True),
    (MODE_SELECT,        "選択",         True),
    SEPARATOR,
    (LOOP,               "ループ",       True),
    (SYMMETRY,           "対称",         True),
    (AUTO,               "自動",         True),
    (AUTO_OPERATION,     "自動カット",   False),   # アイコンとラベルは今の操作に合わせて替える (context._sync_panel)
    SEPARATOR,
    (CUT,                "カット",       False),
    (SEW,                "縫合",         False),
    (DELETE_ALL,         "全削除",       False),
)

# マーキングメニュー (ビューで Shift+右クリック。tool.marking_menu) の項目。置き場所が None なら下のリスト
#   (ID, 置き場所)                  操作 (表示名とチェックは tool_actions.ToolActions.states)
#   (表示名, 置き場所, (子の項目))  子のマーキングメニュー (Maya の対称のメニューと同じく、子も置き場所で並べる)
MARKING_MENU = (
    ("対称", "N", (
        (SYMMETRY,          "N"),
        ("mirrorWorld",     "W"),
        ("mirrorObject",    "E"),
        ("mirrorX",         "SW"),
        ("mirrorY",         "S"),
        ("mirrorZ",         "SE"),
    )),
    ("モード", "W", (
        (MODE_CREATE,       "N"),
        (MODE_EDIT,         "E"),
        (MODE_SELECT,       "S"),
        (LOOP,              "W"),
    )),
    ("自動", "E", (
        (AUTO,              "N"),
        ("autoCut",         "E"),
        ("autoSew",         "S"),
        (DELETE_ON_COMPLETE, "W"),
    )),
    (CUT,               "SE"),
    (SEW,               "SW"),
    (SPLIT,             None),
    (JOIN,              None),
    (DELETE_ALL,        None),
    (SHOW_PANEL,        None),
)

# ツールのキー (Qt の Key_ のあとの名前 -> 操作。"Shift+" を付けると Shift と一緒のとき)。マウスがビューの上のときだけ (tool.view_input)
KEY_ACTIONS = {
    "Tab":      TOGGLE_MODE,
    "L":        LOOP,
    "X":        SYMMETRY,
    "A":        AUTO,
    "Shift+A":  AUTO_OPERATION,
    "C":        CUT,
    "S":        SEW,
}

HELP_TEXTS = {
    MODE_CREATE: "作成: クリックで頂点に点を足す (点の間は最短パス) / Delete: 最後の点を消す / Enter・右クリック: 確定 / Esc: 捨てる / Ctrl+Z: 1 つ戻す / Tab: 次のモードへ / C・S: カット・縫合 / X: 対称 / Shift+右クリック: メニュー / A: 自動 (点を足すたびにカット・縫合) / Shift+A: 自動のカット・縫合を切り替え",
    MODE_EDIT:   "編集: クリック・矩形でガイドを選ぶ (選んでいれば矩形は点を選ぶ。Shift 切り替え / Ctrl 外す / Ctrl+Shift 足す) / 点: ドラッグで動かす (選んでいる点もまとめて)・クリックで選ぶ / 選んだガイドの線: クリックで点を挿入 / Delete: 点 (無ければガイド) を消す / メニューの切り離す (選んだ点で)・接続する (2 本の端どうし・1 本は閉じる) / Tab: 次のモードへ / C・S: カット・縫合 / X: 対称",
    MODE_SELECT: "選択: クリック・ダブルクリック (ループ)・矩形でエッジを選ぶ (Shift 切り替え / Ctrl 外す) / L: ループの事前ハイライト / C・S: 選んだエッジをカット・縫合 / Tab: 次のモードへ / X: 対称",
}
