"""
パネルをアクティブなビューの下の中央に置き、ビューに付いて回らせる (Qt だけ。Maya は知らない)。
"""

from ..compat.qt import QtCore, pointer_of

_INTERVAL   = 250   # 見回りの間隔 (ミリ秒)
_MARGIN     = 12    # ビューの下の端からの余白 (ピクセル)


class PanelFollower(QtCore.QObject):
    """0.25 秒ごとにビューを見回り、パネルをビューの下の中央に置き直す (ビューより広ければ折り返させる)。

    ビューは view_provider() で受け取る (Maya のことは呼ぶ側が知っている)。ビューが無い・見えていない・
    持ち主のウィンドウが最小化されているときはパネルを隠す。パネルの子なので、パネルを消せば一緒に止まる。
    イベントフィルターは使わない (最小限の作り。Maya のウィンドウを動かすと、最大 0.25 秒遅れて付いてくる)。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, panel, view_provider):
        super().__init__(panel)

        self._panel         = panel
        self._view_provider = view_provider
        self._timer         = QtCore.QTimer(self)

        self._timer.timeout.connect(self.place)
        self._timer.start(_INTERVAL)

    # -- 公開メソッド ---------------------------------------------------------
    def place(self):
        """パネルを今のビューの下の中央に置く (隠すべきなら隠す)。"""
        panel = self._panel
        view  = self._view_provider()
        if view is None or not view.isVisible() or view.window().isMinimized():
            panel.hide()
            return

        owner = view.window()
        if pointer_of(panel.parentWidget()) != pointer_of(owner):
            # ビューを切り離して浮かせたら、浮いたウィンドウを持ち主にする (フラグを渡さないと子ウィジェットに戻る)
            panel.setParent(owner, panel.windowFlags())

        panel.fitWidth(view.width() - _MARGIN * 2)   # 狭いビューでは折り返して収める

        corner = view.mapToGlobal(QtCore.QPoint(0, 0))
        x      = corner.x() + (view.width() - panel.width()) // 2
        y      = corner.y() + view.height() - panel.height() - _MARGIN
        if (panel.x(), panel.y()) != (x, y):
            panel.move(x, y)

        if not panel.isVisible():
            # 前に出すのは出し直すときだけ (毎回 raise_ すると、ほかの浮いたウィンドウの上に割り込む)
            panel.show()
            panel.raise_()
