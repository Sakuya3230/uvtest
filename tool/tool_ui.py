# -*- coding: utf-8 -*-
"""
ツール設定のウィンドウ (段階 12)。MEL は core/tool_ui_text.py が表から組み立てる。

    define()        MEL のプロシージャを定義する (import したときに 1 回。リロードでも定義し直す)
    refresh()       開いているウィンドウの値を、今の設定に合わせる (ボタン・キーで変えたとき)
    color_value(k)  色の設定の値 [r, g, b] (ウィンドウの MEL が python() で呼ぶ)
    maya_symmetry_text()  Maya の対称が効いていればその説明 (無ければ "")。対称の欄の表示 (段階 17)

Maya は、ツールのアイコンをダブルクリックしたとき (と、ツールを有効にしたとき) に、
<stringClassName>Properties / <stringClassName>Values の MEL を呼ぶ。プロシージャはそれより前に
定義しておく必要があるので、このモジュールを import したとき (コンテキストのモジュールが import する
= プラグインを読み込んだとき) に定義する。リロードで import し直すと、新しい表で定義し直す。
"""
import maya.mel as mel

from ..core.settings import Settings
from ..core.tool_ui_text import CLASS_NAME, tool_ui_mel
from ..scene.mirror import maya_plane, plane_text
from ..scene.prefs import OptionVarStorage

__all__ = ["define", "refresh", "color_value", "maya_symmetry_text", "CLASS_NAME"]


def define():
    """ツール設定のウィンドウの MEL のプロシージャを定義する。"""
    mel.eval(tool_ui_mel())


def color_value(key):
    """色の設定の値 [r, g, b] (ツール設定のウィンドウの MEL が python() で呼ぶ)。

    コンテキストのコマンドの問い合わせは数を 1 つしか返せないので、色は MEL から Python を呼んで
    受け取る。設定は変えるたびに optionVar に保存されるので、保存先から読めば今の値になる。
    MEL の python() は、Python のリストを MEL の float の配列にして返す。
    """
    return [float(c) for c in Settings(OptionVarStorage()).value(key)]


def maya_symmetry_text():
    """Maya の対称が効いていれば「Maya の対称: ワールド Z  許容値 0.1」、無ければ ""。

    ウィンドウの SetValues が python() で呼び、空でなければ空間・軸・許容値を灰色にする。
    """
    plane = maya_plane()
    if plane is None:
        return ""
    # 欄の幅に収まるよう短くする (「を使います」まで入れると見切れた)
    return "Maya の対称: {}  許容値 {:g}".format(plane_text(plane), plane.tolerance)


def refresh():
    """開いているウィンドウの値を合わせる (ウィンドウが無い・別のツールなら何もしない)。"""
    try:
        mel.eval("{}RefreshUI".format(CLASS_NAME))
    except RuntimeError:
        pass


define()
