"""
丸いボタン (アイコン + 下にラベル)。
"""

from ..compat.qt import QtCore, QtGui, QtWidgets
from .icons import draw_icon

_DIAMETER       = 32    # 丸の直径 (ピクセル。倍率 1 のとき)
_LABEL_HEIGHT   = 13    # ラベルの高さ
_LABEL_PIXELS   = 10    # ラベルの字の大きさ (ピクセル)
_WIDTH          = 52    # ボタン全体の幅 (ラベルが入るように丸より広い。「自動カット」の 5 文字が入る幅)
_MIN_LABEL      = 7     # 小さくしても、これより小さい字にはしない (読めなくなるため)

_NORMAL_FILL    = QtGui.QColor(70, 74, 82)
_HOVER_FILL     = QtGui.QColor(250, 210, 60)     # ホバー: 黄色
_ACTIVE_FILL    = QtGui.QColor(110, 200, 245)    # 押している間・選ばれている: 水色
_RING           = QtGui.QColor(30, 32, 36)
_HOVER_RING     = QtGui.QColor(250, 210, 60)
_LIGHT_ICON     = QtGui.QColor(235, 238, 242)    # 暗い塗りの上のアイコン
_DARK_ICON      = QtGui.QColor(30, 32, 36)       # 明るい塗りの上のアイコン
_LABEL_COLOR    = QtGui.QColor(225, 228, 232)


class RoundButton(QtWidgets.QAbstractButton):
    """丸の中にアイコン、下にラベルを描くボタン。

    色: 普通 = 灰 / ホバー = 黄 / 押している間・選ばれている (切り替えのボタンで checked) = 水色。
    選ばれているボタンにホバーしたときは、塗りは水色のまま縁を黄色にする。アイコンは ui.icons の名前で指す。
    大きさは倍率 scale (1 = 標準。丸・ラベル・字・幅をまとめて変える。setScale で替えられる)。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, icon_name, label, scale=1.0, parent=None):
        super().__init__(parent)
        self.setText(label)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setCursor(QtCore.Qt.PointingHandCursor)

        self._icon_name = icon_name
        self.setScale(scale)

    # -- 上書きするメソッド (QAbstractButton) ---------------------------------
    def hitButton(self, position):
        # 丸の上だけを押せる所にする (ラベルや角の外では押せない)
        center = self._circle_rect().center()
        dx     = position.x() - center.x()
        dy     = position.y() - center.y()

        return dx * dx + dy * dy <= (self._diameter / 2.0) ** 2

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        fill, ring  = self._colors()
        circle      = self._circle_rect()
        painter.setPen(QtGui.QPen(ring, 2.0))
        painter.setBrush(fill)
        painter.drawEllipse(circle)

        icon_color = _DARK_ICON if fill != _NORMAL_FILL else _LIGHT_ICON
        icon_size  = self._diameter * 0.5
        icon_rect  = QtCore.QRectF(circle.center().x() - icon_size / 2, circle.center().y() - icon_size / 2,
                                   icon_size, icon_size)
        draw_icon(painter, self._icon_name, icon_rect, icon_color)

        painter.setPen(_LABEL_COLOR)
        label_rect = QtCore.QRectF(0, circle.bottom() + 2, self.width(), self._label_height)
        painter.drawText(label_rect, QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop, self.text())

    # -- 公開メソッド ---------------------------------------------------------
    def iconName(self):
        return self._icon_name

    def setIconName(self, icon_name):
        self._icon_name = icon_name
        self.update()

    def setScale(self, scale):
        """倍率を替える (大きさ・字を作り直す)。"""
        self._diameter     = int(round(_DIAMETER * scale))
        self._label_height = int(round(_LABEL_HEIGHT * scale))
        self.setFixedSize(int(round(_WIDTH * scale)), button_height(scale))
        font = self.font()
        font.setPixelSize(max(_MIN_LABEL, int(round(_LABEL_PIXELS * scale))))
        self.setFont(font)
        self.update()

    # -- 非公開メソッド -------------------------------------------------------
    def _circle_rect(self):
        return QtCore.QRectF((self.width() - self._diameter) / 2.0 + 1, 1, self._diameter - 2, self._diameter - 2)

    def _colors(self):
        # (塗り, 縁)
        hovered = self.underMouse()
        if self.isDown():
            return _ACTIVE_FILL, _RING

        if self.isChecked():
            return _ACTIVE_FILL, _HOVER_RING if hovered else _RING

        if hovered:
            return _HOVER_FILL, _RING

        return _NORMAL_FILL, _RING


def button_height(scale=1.0):
    """倍率 scale のボタン全体の高さ (ピクセル。区切り線もこの高さにする)。"""
    return int(round(_DIAMETER * scale)) + int(round(_LABEL_HEIGHT * scale)) + 2
