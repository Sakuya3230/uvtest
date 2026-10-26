"""
ビューのパネルを開く / 閉じる (Maya のビューと、Maya を知らない ui のパネルをつなぐ)。
"""

from ..compat.qt import QtWidgets, wrap_instance
from ..ui.panel_follower import PanelFollower
from ..ui.view_panel import ViewPanel, remove_panels
from ..utils import view
from ..core.settings import settings
from .actions import PANEL_ACTIONS


def open_panel(handler):
    """パネルを開き、アクティブなビューの下の中央に付いて回らせる。ボタンを押すと handler(ID) を呼ぶ。"""
    remove_panels()   # 前のものが残っていれば消す (リロードのあとなど)

    active = _active_view_widget()
    owner  = active.window() if active is not None else None
    panel  = ViewPanel(PANEL_ACTIONS, owner, settings.current().value("panelScale"))   # 大きさは設定 panelScale
    panel.actionTriggered.connect(handler)

    follower = PanelFollower(panel, _active_view_widget)   # パネルの子 (パネルを消せば一緒に消える)
    follower.place()

    return panel


def place_panel(panel):
    """パネルを今のビューの下の中央に、すぐ置き直す (大きさを変えた直後など。見回りの 0.25 秒を待たない)。"""
    follower = panel.findChild(PanelFollower) if panel is not None else None
    if follower is not None:
        follower.place()


def close_panel(panel):
    if panel is not None:
        panel.close()   # WA_DeleteOnClose なので C++ の側も消える


def _active_view_widget():
    pointer = view.active_view_pointer()
    if pointer is None:
        return None

    return wrap_instance(pointer, QtWidgets.QWidget)
