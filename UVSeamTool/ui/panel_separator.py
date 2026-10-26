"""
パネルのボタンの組の間に置く縦の区切り線。
"""

from ..compat.qt import QtCore, QtGui, QtWidgets

WIDTH   = 9                             # 区切りの幅 (線の左右の余白を含む。倍率 1 のとき)
_COLOR  = QtGui.QColor(90, 96, 108)


class PanelSeparator(QtWidgets.QWidget):
    """縦の細い線を真ん中に描くだけの部品 (ui.view_panel.ViewPanel がボタンの組の間に置く)。"""

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, height, parent=None, scale=1.0):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setSize(height, scale)

    # -- 公開メソッド ---------------------------------------------------------
    def setSize(self, height, scale=1.0):
        """高さと倍率 (幅) を替える。"""
        self.setFixedSize(int(round(WIDTH * scale)), height)
        self.update()

    # -- 上書きするメソッド (QWidget) -----------------------------------------
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QPen(_COLOR, 1.0))
        x = self.width() // 2
        painter.drawLine(x, 4, x, self.height() - 4)
