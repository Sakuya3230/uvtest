"""
設定の項目の表。項目を足すときは、ここに 1 行足して、使う所で settings.current().value("キー") を引く。
"""

from __future__ import annotations

from .setting import BOOL, CHOICE, COLOR, FLOAT, Setting

_PATH       = "パス"
_SYMMETRY   = "対称"
_APPLY      = "カット / 縫合"
_EXIT       = "ツールを抜けるとき"
_DISPLAY    = "表示"
_COLORS     = "色"

DEFINITIONS = (
    # パス: 曲がりの少ないパスを選ぶ重み (0 で長さだけの最短。直角 1 回 = 重み x 平均のエッジの長さの遠回り)
    Setting("straightness",         FLOAT,  1.0,                "まっすぐさ",               _PATH,
            minimum=0.0, maximum=10.0),

    # 対称 (Maya の対称がオン (ワールド / オブジェクト) の間は、Maya の空間・軸・許容値が優先される)
    Setting("symmetry",             BOOL,   False,              "対称",                     _SYMMETRY),
    Setting("mirrorSpace",          CHOICE, "object",           "空間",                     _SYMMETRY,
            choices=(("object", "オブジェクト"), ("world", "ワールド"))),
    Setting("mirrorAxis",           CHOICE, "x",                "軸",                       _SYMMETRY,
            choices=(("x", "X"), ("y", "Y"), ("z", "Z"))),
    Setting("mirrorTolerance",      FLOAT,  0.1,                "許容値",                   _SYMMETRY,
            minimum=0.0001, maximum=10.0),

    # 自動: 作成のモードで点を足すたびに、足した区間へ当てる (編集のモードでは当てない。ガイドは UV の状態を持たないため)
    Setting("autoApply",            BOOL,   False,              "自動",                     _APPLY),
    Setting("autoOperation",        CHOICE, "cut",              "自動のときの操作",         _APPLY,
            choices=(("cut", "カット"), ("sew", "縫合"))),
    # 確定したガイドを、確定と同時に消す (自動で当てたあとは、ガイドをいじらないことが多いため。UV のカット / 縫合は残る)
    Setting("deleteGuideOnComplete", BOOL,  False,              "確定後にガイドを削除",     _APPLY),

    # 作成・編集のモードで抜けたら、ガイドのエッジを選ぶ (選択のモードでは、選んでいたエッジをそのまま残す)
    Setting("selectGuidesOnExit",   BOOL,   True,               "ガイドのエッジを選ぶ",     _EXIT),

    # ビューのパネル (オフでも、キーとマーキングメニュー (Shift+右クリック) で同じ操作ができる)
    Setting("showPanel",            BOOL,   True,               "ビューのパネルを表示",     _DISPLAY),
    # パネル全体の大きさの倍率 (ボタン・字・区切り線・余白をまとめて。1 = 標準)
    Setting("panelScale",           FLOAT,  1.0,                "パネルの大きさ (倍率)",    _DISPLAY,
            minimum=0.5, maximum=2.0),

    # 線の太さと点の大きさ (ピクセル)。選んでいる線は +1、選んでいる点は +3・マウスの下の点は +4・挿入の印は -1 で描く
    Setting("lineWidth",            FLOAT,  3.0,                "ガイドの線の太さ",         _DISPLAY,
            minimum=1.0, maximum=12.0),
    Setting("pointSize",            FLOAT,  10.0,               "ガイドの点の大きさ",       _DISPLAY,
            minimum=4.0, maximum=30.0),

    # 確定したガイドはマゼンタ (Maya のエッジの選択モードのエッジの青と見分けるため)。
    # 作成中のガイドは選んでいるガイドと同じ橙 (今、手を入れているガイドが作成でも編集でも同じ色で分かるように)
    Setting("guideColor",           COLOR,  (1.00, 0.30, 0.85), "確定したガイド",           _COLORS),
    Setting("activeColor",          COLOR,  (1.00, 0.55, 0.10), "作成中のガイド",           _COLORS),
    Setting("selectedColor",        COLOR,  (1.00, 0.55, 0.10), "選んでいるガイド",         _COLORS),
    Setting("cutColor",             COLOR,  (1.00, 0.20, 0.20), "カットしたエッジ",         _COLORS),
    Setting("hoverGuideColor",      COLOR,  (1.00, 0.70, 0.95), "マウスの下のガイド",       _COLORS),
    Setting("pointColor",           COLOR,  (0.25, 1.00, 0.35), "ガイドの点",               _COLORS),
    Setting("hoverPointColor",      COLOR,  (1.00, 0.95, 0.30), "マウスの下の点",           _COLORS),
    Setting("selectedPointColor",   COLOR,  (1.00, 0.20, 0.20), "選んでいる点",             _COLORS),
    Setting("insertColor",          COLOR,  (1.00, 1.00, 1.00), "点を挿入できる場所",       _COLORS),
    Setting("previewColor",         COLOR,  (1.00, 0.85, 0.20), "プレビュー",               _COLORS),
    Setting("hoverEdgeColor",       COLOR,  (1.00, 1.00, 0.40), "マウスの下のエッジ",       _COLORS),
    Setting("loopColor",            COLOR,  (1.00, 1.00, 0.40), "ループの事前ハイライト",   _COLORS),
    Setting("mirrorColor",          COLOR,  (0.70, 0.70, 0.40), "反対側 (対称)",            _COLORS),
    Setting("hoverVertexColor",     COLOR,  (1.00, 0.60, 0.15), "マウスの下の頂点",         _COLORS),
)

BY_KEY = {setting.key: setting for setting in DEFINITIONS}
