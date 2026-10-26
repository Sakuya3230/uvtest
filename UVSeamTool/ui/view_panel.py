"""
ビューの上に出すボタンのパネル (Qt だけ。Maya は知らない)。
"""

from ..compat.qt import QtCore, QtGui, QtWidgets
from .panel_separator import PanelSeparator
from .round_button import RoundButton, button_height

OBJECT_NAME = "UVSeamToolViewPanel"   # リロードのあとでも見つけて消せるように
SEPARATOR   = None                    # ボタンの列の中に置くと、そこに区切り線を入れる

_BACKGROUND = QtGui.QColor(30, 32, 36, 215)
_BORDER     = QtGui.QColor(90, 140, 210)
_MARGINS    = (6, 5, 6, 4)      # 左・上・右・下の余白 (倍率 1 のとき)
_ROW_GAP    = 2                 # 段の間 (倍率 1 のとき)


class ViewPanel(QtWidgets.QWidget):
    """丸いボタン (ui.round_button.RoundButton) を横に並べた、枠なしの Tool ウィンドウ。

    ボタンは (ID, 表示名, 切り替えか) か SEPARATOR (区切り線) の列で受け取り、押されたら actionTriggered(ID) を出す。
    何をするかは知らない。アイコンは ID と同じ名前のもの (ui.icons) を描く。
    幅が足りなければ折り返して何段かにする (fitWidth。ビューを狭くしたとき)。段の端に来た区切り線は出さない。
    部品の位置は自分で決める (レイアウトを使わない。折り返しの並べ直しを簡単にするため)。
    押してもフォーカスを奪わない (WindowDoesNotAcceptFocus) ので、押したあとも Maya のキーが効く。
    全体の大きさは倍率 scale (1 = 標準。ボタン・字・区切り線・余白をまとめて変える。setScale で替えられる)。
    """

    actionTriggered = QtCore.Signal(str)

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, actions, owner, scale=1.0):
        super().__init__(owner)
        flags = (QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint
                 | QtCore.Qt.WindowDoesNotAcceptFocus)
        self.setWindowFlags(flags)
        self.setObjectName(OBJECT_NAME)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)    # 角の外を透かす
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)    # 出しただけでフォーカスを奪わない
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self._buttons   = {}            # ID -> RoundButton
        self._items     = []            # 並べる順の部品 (RoundButton か PanelSeparator)
        self._rows      = None          # 今の段の分け方 (段ごとの部品の番号の列。_arrange で決める)
        self._scale     = scale         # 倍率
        self._fit       = 10 ** 6       # 最後に fitWidth で受け取った幅

        for action in actions:
            if action is SEPARATOR:
                self._items.append(PanelSeparator(button_height(scale), self, scale))
                continue

            action_id, label, checkable = action
            button = RoundButton(action_id, label, scale, self)   # アイコンは ID と同じ名前 (ui.icons)
            button.setCheckable(checkable)
            button.clicked.connect(lambda checked=False, action_id=action_id: self.actionTriggered.emit(action_id))
            self._buttons[action_id] = button
            self._items.append(button)

        self.fitWidth(10 ** 6)   # 1 段で並べる

    # -- 上書きするメソッド (QWidget) -----------------------------------------
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtGui.QPen(_BORDER, 1.0))
        painter.setBrush(_BACKGROUND)
        painter.drawRoundedRect(QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 6.0, 6.0)

    # -- 公開メソッド ---------------------------------------------------------
    def fitWidth(self, width):
        """幅 width (ピクセル) に収まるよう、段の分け方を決め直す (変わらなければ何もしない)。"""
        self._fit  = width
        separators = {index for index, item in enumerate(self._items) if isinstance(item, PanelSeparator)}
        margins    = self._margins()
        rows       = split_rows([item.width() for item in self._items], separators, width - margins[0] - margins[2])
        if rows != self._rows:
            self._arrange(rows)

    def setScale(self, scale):
        """全体の大きさの倍率を替える (ボタン・区切り線を作り直して、段を並べ直す)。"""
        if scale == self._scale:
            return

        self._scale = scale
        for item in self._items:
            if isinstance(item, PanelSeparator):
                item.setSize(button_height(scale), scale)
            else:
                item.setScale(scale)
        self._rows = None
        self.fitWidth(self._fit)

    def scale(self):
        return self._scale

    def setChecked(self, action_id, checked):
        """切り替えのボタンの見た目を合わせる (押されたことにはしない)。"""
        button = self._buttons[action_id]
        button.blockSignals(True)
        button.setChecked(checked)
        button.blockSignals(False)

    def setAppearance(self, action_id, icon_name, label):
        """ボタンのアイコン (ui.icons の名前) とラベルを替える (今の状態を見せるボタン。「自動の操作」など)。"""
        button = self._buttons[action_id]
        button.setIconName(icon_name)
        button.setText(label)
        button.update()

    # -- 非公開メソッド -------------------------------------------------------
    def _margins(self):
        # 倍率をかけた余白 (左・上・右・下)
        return tuple(int(round(margin * self._scale)) for margin in _MARGINS)

    def _arrange(self, rows):
        # rows (段ごとの部品の番号) のとおりに部品を置き、パネルの大きさを合わせる。段に入らない区切り線は隠す
        self._rows  = rows
        placed      = {index for row in rows for index in row}
        margins     = self._margins()
        gap         = int(round(_ROW_GAP * self._scale))
        height      = button_height(self._scale)
        width       = 0
        y           = margins[1]
        for row in rows:
            x = margins[0]
            for index in row:
                item = self._items[index]
                item.move(x, y)
                x += item.width()
            width = max(width, x)
            y    += height + gap

        for index, item in enumerate(self._items):
            item.setVisible(index in placed)

        self.setFixedSize(width + margins[2], y - gap + margins[3])
        self.update()


def split_rows(widths, separators, width):
    """部品の幅の列を、幅 width に収まる段に分ける (段ごとの部品の番号の列)。

    separators は区切り線の番号。段の始め・終わりに来た区切り線は落とす。1 つも入らない幅でも、1 段に 1 つは置く。
    """
    rows = [[]]
    used = 0
    for index, item_width in enumerate(widths):
        row = rows[-1]
        if row and used + item_width > width:
            rows.append([])
            row  = rows[-1]
            used = 0

        if index in separators and not row:
            continue   # 段の始めの区切り線

        row.append(index)
        used += item_width

    rows = [row[:-1] if row and row[-1] in separators else row for row in rows]

    return [row for row in rows if row]


def remove_panels():
    """残っているパネルを objectName で探して消す (リロードの前など)。"""
    app = QtWidgets.QApplication.instance()
    if not isinstance(app, QtWidgets.QApplication):
        return

    for widget in app.allWidgets():
        if widget.objectName() == OBJECT_NAME:
            widget.hide()
            widget.deleteLater()
