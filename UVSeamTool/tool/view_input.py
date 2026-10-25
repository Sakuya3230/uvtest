"""
ビューの右クリック・ダブルクリック・ドラッグ中の Esc・ツールのキーを、Maya より先に受け取る。
"""

from ..compat.qt import QtCore, QtGui, QtWidgets, pointer_of
from ..utils import view

# 文字を打つ欄 (ここにフォーカスがあるときは、ツールのキーを取らない)
_TEXT_WIDGETS = (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit, QtWidgets.QAbstractSpinBox)


class ViewInputFilter(QtCore.QObject):
    """アプリ全体のイベントフィルター。コンテキストのメソッドでは受け取れない入力を受け取る。

    - 右クリック: コンテキストの MEvent には右ボタンが無い (マーキングメニューに使われる)。3D のビューで右ボタンを
      押したら right_click() を呼び、True なら押した・離したイベントを Maya に渡さない
    - ダブルクリック: 2 回目の押下はコンテキストの doPress に届かない。3D のビューで左ボタンをダブルクリックしたら
      double_click(x, y, shift, ctrl) を呼び (x, y はビューのピクセル。左下が原点で MEvent と同じ)、True なら
      ダブルクリックと、続いて届く左ボタンの離しを Maya に渡さない (渡すと Maya が 1 本だけの選択に戻すことがある)
    - ドラッグ中の Esc: マウスのボタンを押している間は、Maya がコンテキストの abortAction を呼ばない。
      is_busy() が True (途中の操作がある) の間だけ Esc を受け取って cancel() を呼ぶ。それ以外の Esc は Maya に任せる
    - ツールのキー: shortcuts ({キーの名前: 呼ぶ関数}。名前は Qt の Key_ のあと。"Tab"・"C" など。"Shift+A" のように
      "Shift+" を付けると Shift と一緒のとき) のキーを、マウスが 3D のビューの上にあり、文字を打つ欄にフォーカスが無く、
      修飾キーが名前のとおりのときだけ取る (Ctrl+S などは Maya に渡す)。押しっぱなしの繰り返しは取るだけで、関数は呼ばない
    - ホイール: 3D のビューの上で Shift か Ctrl を押しながら回したら wheel(目盛り, shift, ctrl) を呼び、True なら Maya に
      渡さない (修飾キーなしのホイールはいつもカメラのズーム)。目盛りは 1 刻み (手前に回すと負)
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, right_click, double_click, is_busy, cancel, shortcuts, wheel=None):
        super().__init__()

        self._right_click   = right_click
        self._double_click  = double_click
        self._is_busy       = is_busy
        self._cancel        = cancel
        self._shortcuts     = {_key_of(name): action for name, action in shortcuts.items()}   # (キー, Shift か) -> 関数
        self._wheel         = wheel
        self._swallow       = set()     # 押したのを受け取ったボタン (次の離しも Maya に渡さない)

    # -- 上書きするメソッド (QObject) -----------------------------------------
    def eventFilter(self, watched, event):
        event_type = event.type()
        if event_type in (QtCore.QEvent.ShortcutOverride, QtCore.QEvent.KeyPress):
            return self._filter_escape(event) or self._filter_shortcut(event)

        if event_type == QtCore.QEvent.MouseButtonRelease:
            if event.button() in self._swallow:
                self._swallow.discard(event.button())
                return True
            return False

        if event_type == QtCore.QEvent.MouseButtonPress:
            return self._filter_right_button(watched, event)

        if event_type == QtCore.QEvent.MouseButtonDblClick:
            return self._filter_double_click(watched, event)

        if event_type == QtCore.QEvent.Wheel:
            return self._filter_wheel(watched, event)

        return False

    # -- 公開メソッド ---------------------------------------------------------
    def install(self):
        QtWidgets.QApplication.instance().installEventFilter(self)

    def uninstall(self):
        QtWidgets.QApplication.instance().removeEventFilter(self)

    # -- 非公開メソッド -------------------------------------------------------
    def _filter_escape(self, event):
        if event.key() != QtCore.Qt.Key_Escape or not self._is_busy():
            return False

        if event.type() == QtCore.QEvent.ShortcutOverride:
            event.accept()   # Maya のホットキーより先に、次の KeyPress を受け取る
            return True

        self._cancel()

        return True

    def _filter_shortcut(self, event):
        modifiers = event.modifiers() & ~QtCore.Qt.KeypadModifier
        if modifiers not in (QtCore.Qt.NoModifier, QtCore.Qt.ShiftModifier):
            return False

        action = self._shortcuts.get((event.key(), modifiers == QtCore.Qt.ShiftModifier))
        if action is None:
            return False

        if self._typing() or not self._is_view(QtWidgets.QApplication.widgetAt(QtGui.QCursor.pos())):
            return False

        if event.type() == QtCore.QEvent.ShortcutOverride:
            event.accept()   # Maya のホットキーより先に、次の KeyPress を受け取る
            return True

        if not event.isAutoRepeat():
            action()

        return True

    def _filter_wheel(self, watched, event):
        modifiers = event.modifiers()
        shift     = bool(modifiers & QtCore.Qt.ShiftModifier)
        ctrl      = bool(modifiers & QtCore.Qt.ControlModifier)
        if self._wheel is None or not (shift or ctrl) or not self._is_view(watched):
            return False

        delta = event.angleDelta()
        steps = (delta.y() or delta.x()) / 120.0   # Shift で横のホイールに変わる環境もあるので、縦が 0 なら横を使う
        if steps == 0:
            return False

        return bool(self._wheel(steps, shift, ctrl))

    def _filter_right_button(self, watched, event):
        if event.button() != QtCore.Qt.RightButton or not self._is_view(watched):
            return False

        if event.modifiers() & QtCore.Qt.ShiftModifier:
            return False   # Shift+右クリックは Maya に渡す (ツールのマーキングメニュー)

        if not self._right_click():
            return False

        self._swallow.add(QtCore.Qt.RightButton)

        return True

    def _filter_double_click(self, watched, event):
        if event.button() != QtCore.Qt.LeftButton:
            return False

        widget = self._view_of(watched)
        if widget is None:
            return False

        local     = widget.mapFromGlobal(QtGui.QCursor.pos())
        modifiers = event.modifiers()
        shift     = bool(modifiers & QtCore.Qt.ShiftModifier)
        ctrl      = bool(modifiers & QtCore.Qt.ControlModifier)
        if not self._double_click(local.x(), widget.height() - 1 - local.y(), shift, ctrl):
            return False

        self._swallow.add(QtCore.Qt.LeftButton)

        return True

    def _typing(self):
        # 文字を打つ欄にフォーカスがあるか
        return isinstance(QtWidgets.QApplication.focusWidget(), _TEXT_WIDGETS)

    def _is_view(self, watched):
        # ウィジェットが 3D のビューの描画面 (かその子) か
        return self._view_of(watched) is not None

    def _view_of(self, watched):
        # ウィジェットを含む 3D のビューの描画面 (無ければ None)
        if not isinstance(watched, QtWidgets.QWidget):
            return None

        views  = view.view_widget_pointers()
        widget = watched
        while widget is not None:
            if pointer_of(widget) in views:
                return widget
            widget = widget.parentWidget()

        return None


def _key_of(name):
    # "Tab" -> (Key_Tab, False)、"Shift+A" -> (Key_A, True)
    shift = name.startswith("Shift+")
    if shift:
        name = name[len("Shift+"):]

    return getattr(QtCore.Qt, "Key_" + name), shift
