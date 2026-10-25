"""
ツール設定のウィンドウ (ツールのアイコンをダブルクリックで開く)。MEL は Maya が呼ぶ入り口だけで、中身は maya.cmds。

    MEL (define で定義する)                            Python (このモジュール)
    uvSeamToolProperties()                    ->     properties()       部品を作る
    uvSeamToolValues(string $toolName)        ->     values(toolName)   作り直し、コマンドを付け、値を入れる

Maya はコンテキストの stringClassName (constants.TOOL_CLASS) に Properties / Values を付けた名前の MEL の
global proc を呼ぶ。Python の関数の名前では呼ばないので、入り口だけ MEL で定義する (ViewPanelLesson の段階 7c と同じ)。

部品に渡す関数は、渡したときの関数オブジェクトのまま残る。リロードしても新しいコードが動くよう、渡すのは
_command(名前, ...) で、呼ばれるたびに sys.modules から今のこのモジュールを引いて、その名前の関数を呼ぶ。
"""

import sys

import maya.cmds as cmds
import maya.mel as mel

from ..constants import TOOL_CLASS
from ..core.settings import settings
from ..core.settings.definitions import BY_KEY, DEFINITIONS
from ..utils import guide_attribute
from ..utils.selection import selected_meshes
from ..utils.symmetry import maya_symmetry
from . import guide_cleanup, setting_controls

_ICON           = "pythonFamily.png"    # 見出しのアイコン (Maya の組み込み)
_LABEL_WIDTH    = setting_controls.LABEL_WIDTH
_MIRROR_KEYS    = ("mirrorSpace", "mirrorAxis", "mirrorTolerance")   # Maya の対称がオンの間は灰色にする
_BUTTON_WIDTH   = 240                   # ボタンの幅 (横幅いっぱいには広げない)
_SPACING        = 6                     # ボタンなどの行の間の縦の間隔
_GAP            = 6                     # ラベルとボタンの間
_CONTROLS       = {}                    # 設定のキー・ボタンの名前 -> 部品のフルパス (properties で作るたびに作り直す)

_STUB_MEL = """
global proc {name}Properties()
{{
    python("__import__('{module}', fromlist=['x']).properties()");
}}

global proc {name}Values(string $toolName)
{{
    python("__import__('{module}', fromlist=['x']).values('" + $toolName + "')");
}}
"""


def define():
    """Maya が呼ぶ入り口 (MEL の global proc) を定義する。ツールを有効にするたびに呼んでよい。"""
    mel.eval(_STUB_MEL.format(name=TOOL_CLASS, module=__name__))


def open_window():
    """ツール設定のウィンドウを開く。"""
    mel.eval("toolPropertyWindow")


def refresh():
    """開いていれば、設定の値・Maya の対称・保存したガイドの数を入れ直す (部品の -edit では changeCommand は呼ばれない)。"""
    for setting in DEFINITIONS:
        name = _CONTROLS.get(setting.key)
        if name and cmds.control(name, exists=True):
            setting_controls.show(name, setting, settings.current().value(setting.key))

    # Maya の対称がオンの間は、Maya の面が優先されるので、ツールの空間・軸・許容値を灰色にして、Maya の面を見せる
    maya = maya_symmetry()
    for key in _MIRROR_KEYS:
        name = _CONTROLS.get(key)
        if name and cmds.control(name, exists=True):
            setting_controls.set_enabled(name, BY_KEY[key], maya is None)

    note = _CONTROLS.get("mayaSymmetry")
    if note and cmds.control(note, exists=True):
        text = "オフ" if maya is None else "{} {} (許容値 {:g})。こちらが優先されます".format(
            "ワールド" if maya[0] == "world" else "オブジェクト", maya[1].upper(), maya[2])
        cmds.text(note, edit=True, label=text)

    count = _CONTROLS.get("guideCount")
    if count and cmds.control(count, exists=True):
        cmds.text(count, edit=True, label="{} 個".format(len(guide_attribute.meshes_with_guides())))


# -- Maya が呼ぶ (MEL の入り口から) --------------------------------------------------

def properties():
    """部品を作る (コマンドは values で付ける)。"""
    _CONTROLS.clear()
    cmds.setUITemplate("OptionsTemplate", pushTemplate=True)
    try:
        cmds.setParent(cmds.toolPropertyWindow(query=True, location=True))
        cmds.columnLayout(TOOL_CLASS, adjustableColumn=True)
        for category in _categories():
            cmds.frameLayout(label=category, collapsable=True, collapse=False)
            cmds.columnLayout(adjustableColumn=True)
            for setting in DEFINITIONS:
                if setting.category == category:
                    _CONTROLS[setting.key] = setting_controls.make(setting)
            _rows_column()
            if category == BY_KEY["symmetry"].category:
                _CONTROLS["mayaSymmetry"] = _labeled_text("Maya の対称")
            _CONTROLS["reset:" + category] = _labeled_button(category, "既定に戻す")
            cmds.setParent("..")
            cmds.setParent("..")
            cmds.setParent("..")

        cmds.frameLayout(label="保存したガイド", collapsable=True, collapse=False)
        _rows_column()
        _CONTROLS["guideCount"]     = _labeled_text("保存しているメッシュ")
        _CONTROLS["listGuides"]     = _labeled_button("一覧", "スクリプトエディタに出す")
        _CONTROLS["deleteSelected"] = _labeled_button("削除", "選んでいるメッシュのガイド")
        _CONTROLS["deleteAll"]      = _labeled_button("", "シーンのすべてのガイド...")
        cmds.setParent("..")
        cmds.setParent("..")
        cmds.setParent("..")
    finally:
        cmds.setUITemplate(popTemplate=True)


def values(tool_name):
    """作り直してコマンドを付け、値を入れる。見出しと Reset Tool のボタンも。"""
    layout = cmds.toolPropertyWindow(query=True, location=True) + "|" + TOOL_CLASS
    if cmds.layout(layout, exists=True):
        cmds.deleteUI(layout)   # 毎回作り直す (リロードで部品が変わっても新しくなる)
    properties()

    for setting in DEFINITIONS:
        if setting.key in _CONTROLS:
            setting_controls.attach(_CONTROLS[setting.key], setting, _command("control_changed", setting.key))

    for category in _categories():
        cmds.button(_CONTROLS["reset:" + category], edit=True, command=_command("reset_category", category))

    cmds.button(_CONTROLS["listGuides"], edit=True, command=_command("list_guides"))
    cmds.button(_CONTROLS["deleteSelected"], edit=True, command=_command("delete_selected"))
    cmds.button(_CONTROLS["deleteAll"], edit=True, command=_command("delete_all"))
    refresh()

    # 見出し・アイコン (MEL のプロシージャ)。Reset Tool のボタンは、すべての設定を既定に戻す
    mel.eval('toolPropertySetCommon "{}" "{}" "";'.format(tool_name, _ICON))
    reset = cmds.toolPropertyWindow(query=True, resetButton=True)
    if reset and cmds.button(reset, exists=True):
        cmds.button(reset, edit=True, enable=True, command=_command("reset_all"))
    mel.eval("toolPropertySelect {};".format(TOOL_CLASS))


# -- 部品のコマンド (_command で呼ばれる) --------------------------------------------

def control_changed(key):
    name = _CONTROLS.get(key)
    if not name or not cmds.control(name, exists=True):
        return   # リロード直後で部品を覚えていない (ウィンドウを開き直すと values で作り直す)

    settings.current().setValue(key, setting_controls.read(name, BY_KEY[key]))


def reset_category(category):
    settings.current().reset([setting.key for setting in DEFINITIONS if setting.category == category])
    refresh()


def reset_all():
    settings.current().reset()
    refresh()


def list_guides():
    guide_cleanup.list_guides()
    refresh()


def delete_selected():
    guide_cleanup.delete_guides(selected_meshes())
    refresh()


def delete_all():
    guide_cleanup.delete_all_guides(confirm=True)
    refresh()


# -- 非公開 ---------------------------------------------------------------------------

def _rows_column():
    # ラベル付きのボタンの行を並べる列。adjustableColumn にしない (するとボタンが横幅いっぱいに広がる)
    cmds.columnLayout(adjustableColumn=False, rowSpacing=_SPACING)
    cmds.separator(style="none", height=2)   # 上の部品との間をあける


def _labeled_row(label):
    # 左の列 (幅 _LABEL_WIDTH。色のスライダーのラベルと同じ) に右寄せのラベル。右の列に部品を 1 つ置く
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(_LABEL_WIDTH, _BUTTON_WIDTH + _GAP),
                   columnAttach2=("right", "left"), columnOffset2=(0, _GAP))
    cmds.text(label=label, align="right")


def _labeled_button(label, button_label):
    _labeled_row(label)
    button = cmds.button(label=button_label, width=_BUTTON_WIDTH)
    cmds.setParent("..")

    return button


def _labeled_text(label):
    _labeled_row(label)
    text = cmds.text(label="", align="left")
    cmds.setParent("..")

    return text


def _categories():
    # 表に出てくる順の欄の名前 (重なりなし)
    categories = []
    for setting in DEFINITIONS:
        if setting.category not in categories:
            categories.append(setting.category)

    return categories


def _command(name, *bound):
    # 部品に渡すコマンド: 部品が渡す引数 (値など) は捨て、呼ばれるたびに今のこのモジュールの name を呼ぶ
    def command(*_ignored):
        return getattr(sys.modules[__name__], name)(*bound)

    return command
