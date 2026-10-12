# -*- coding: utf-8 -*-
"""
キー (段階 11)。操作の表 (core.actions の key) のキーを、Qt のイベントフィルターで受け取る。

    keys.install(context.runAction)   # ツールを有効にしたとき
    keys.uninstall()                  # ツールを無効にしたとき

仕組み:
- API 2.0 のコンテキスト (MPxContext) にはキーのイベントが無い (Esc だけは abortAction が呼ばれる)。
  そこで Qt のアプリケーションにイベントフィルター (QObject.eventFilter) を付けて、Maya の
  ウィジェットに届く前のキーを見る (ウェイトスライダー・旧版と同じ方式)
- 受け取るのは、マウスが 3D ビューの上にあり、文字の入力欄にフォーカスが無く、修飾キーが表の
  とおり (Tab は修飾キーなし、クリアは Shift+Esc) のときだけ。それ以外は Maya にそのまま渡す
- Maya のホットキー (C = カーブにスナップ、S = キーの設定など) より先に受け取るため、
  ShortcutOverride のイベントを accept する。Qt はキーを押すと、まず ShortcutOverride を送り、
  accept されなければショートカット (ホットキー) として扱う。accept すると KeyPress が届く
- Tab は Qt ではフォーカスの移動に使われるが、アプリケーションのフィルターで先に消費すれば
  フォーカスは動かない (旧版の GUI で確認)
- 押しっぱなしの自動の繰り返し (isAutoRepeat) では実行しない
- フィルターはツールを有効にしている間だけ付ける。外さないと、ツールを抜けても C / S を取り続け、
  リロードしたあとは古いコードが呼ばれ続ける
"""
import maya.cmds as cmds

from ..core.actions import key_bindings

__all__ = ["install", "uninstall", "installed", "pointer_over_view", "qt_key_table"]

_FILTER = []   # 付けているフィルター (1 つだけ)


def _qt():
    try:
        from PySide6 import QtCore, QtWidgets
    except ImportError:
        from PySide2 import QtCore, QtWidgets
    return QtCore, QtWidgets


def qt_key_table():
    """{(Qt のキー, Shift, Ctrl): 操作の ID} (操作の表から)。"""
    QtCore, _QtWidgets = _qt()
    return {(getattr(QtCore.Qt, "Key_" + binding.name), binding.shift, binding.ctrl): action_id
            for binding, action_id in key_bindings()}


def pointer_over_view():
    """マウスが 3D ビューの上にあり、文字の入力欄にフォーカスが無いか。"""
    _QtCore, QtWidgets = _qt()
    typing = (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit,
              QtWidgets.QAbstractSpinBox)
    if isinstance(QtWidgets.QApplication.focusWidget(), typing):
        return False
    panel = cmds.getPanel(underPointer=True)
    return bool(panel) and cmds.getPanel(typeOf=panel) == "modelPanel"


def install(callback, eligible=pointer_over_view, double_click=None, wheel=None):
    """キーのフィルターを付ける (付いていれば付け替える)。callback(操作の ID) を呼ぶ。

    eligible() -> bool は受け取ってよいか (テストで差し替える)。Qt のアプリケーションが無ければ何もしない。
    double_click(shift, ctrl) -> bool を渡すと、ビューの上の左ボタンのダブルクリック (Qt の
    MouseButtonDblClick) でも呼ぶ (段階 16d)。True を返したら、そのイベントは Maya に渡さない。
    Maya は 2 回目の押下をコンテキストに届けないので、ダブルクリックはここで受け取る。
    wheel(delta, shift, ctrl) -> bool を渡すと、ビューの上のホイールで呼ぶ (段階 21。輪切りの微調整)。
    True を返したら Maya に渡さない (カメラのズームにしない)。delta は縦 (無ければ横) の回転量。
    """
    uninstall()
    QtCore, QtWidgets = _qt()
    app = QtWidgets.QApplication.instance()
    if app is None:
        return None
    table = qt_key_table()
    qt = QtCore.Qt

    class KeyFilter(QtCore.QObject):
        def eventFilter(self, obj, event):
            kind = event.type()
            if kind == QtCore.QEvent.Wheel:
                if wheel is None or not eligible():
                    return False
                angle = event.angleDelta()
                delta = angle.y() or angle.x()   # Shift+ホイールを横の回転にする環境がある
                modifiers = event.modifiers()
                return bool(wheel(delta, bool(modifiers & qt.ShiftModifier),
                                  bool(modifiers & qt.ControlModifier)))
            if kind == QtCore.QEvent.MouseButtonDblClick:
                if double_click is None or event.button() != qt.LeftButton or not eligible():
                    return False
                modifiers = event.modifiers()
                return bool(double_click(bool(modifiers & qt.ShiftModifier),
                                         bool(modifiers & qt.ControlModifier)))
            if kind not in (QtCore.QEvent.ShortcutOverride, QtCore.QEvent.KeyPress):
                return False
            modifiers = event.modifiers()
            if modifiers & ~(qt.ShiftModifier | qt.ControlModifier | qt.KeypadModifier):
                return False   # Alt など、表に無い修飾キー
            key = (event.key(), bool(modifiers & qt.ShiftModifier), bool(modifiers & qt.ControlModifier))
            action_id = table.get(key)
            if action_id is None or not eligible():
                return False
            if kind == QtCore.QEvent.ShortcutOverride:
                event.accept()   # ホットキーより先に受け取る (このあと KeyPress が届く)
                return True
            if not event.isAutoRepeat():
                callback(action_id)
            return True

    key_filter = KeyFilter()
    app.installEventFilter(key_filter)
    _FILTER.append(key_filter)
    return key_filter


def uninstall():
    """付けているフィルターを外す (付いていなければ何もしない)。"""
    if not _FILTER:
        return
    _QtCore, QtWidgets = _qt()
    app = QtWidgets.QApplication.instance()
    for key_filter in _FILTER:
        if app is not None:
            app.removeEventFilter(key_filter)
    del _FILTER[:]


def installed():
    return bool(_FILTER)
