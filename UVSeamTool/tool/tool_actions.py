"""
ツールの操作 (パネルのボタン・キー・マーキングメニュー) を受けて当てる。パネルとマーキングメニューの出し入れも。
"""

from ..compat.qt import QtCore
from ..core.settings import settings
from ..utils import log, view
from . import guide_cleanup, panel_host, tool_settings_window
from .actions import (AUTO, AUTO_OPERATION, DELETE_ALL, DELETE_ON_COMPLETE, JOIN, KEY_ACTIONS, LOOP, MODE_SELECT, MODES, PANEL_ACTIONS,
                      SET_SETTINGS, SHOW_PANEL, SPLIT, SYMMETRY, TOGGLE_MODE)
from .marking_menu import MarkingMenu
from .symmetry import current_plane, describe

_TOGGLE_SETTINGS = {SYMMETRY: "symmetry", AUTO: "autoApply", SHOW_PANEL: "showPanel",
                    DELETE_ON_COMPLETE: "deleteGuideOnComplete"}   # 設定を切り替えるだけの操作
_WATCH_INTERVAL  = 500   # 新しくできたビューのメニューを差し替える見回りの間隔 (ミリ秒)


class ToolActions:
    """パネルのボタン・キー・マーキングメニューの操作 (actions の ID) を、ツールに当てる。

    ツール (tool.context.UVSeamToolContext) の mode() / setMode() / subTool() / subTools() / targets() を使う。
    パネル (設定 showPanel のときだけ) とマーキングメニューを install で出し、release で消す。
    パネルのボタンとマーキングメニューの見た目 (表示名・チェック) は、どちらも states() で決める。
    設定が変わったら、パネルの見た目・パネルの出し入れ・ツール設定のウィンドウを合わせ、ログで知らせる。
    ツールを使っている間に新しくできたビューにもマーキングメニューが効くよう、0.5 秒ごとに見回る
    (パネルの見回り (ui.panel_follower) とは別。パネルを消している設定でも動くように)。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, tool):
        self._tool          = tool
        self._panel         = None      # ui.view_panel.ViewPanel (install の間で、設定 showPanel のときだけ)
        self._marking_menu  = None      # MarkingMenu (install の間だけ)
        self._view_timer    = None      # 新しいビューの見回り (QTimer。install の間だけ)

    # -- 公開メソッド ---------------------------------------------------------
    def install(self):
        """パネル・マーキングメニューを出し、設定の変更を聞き始める。"""
        self._show_panel(settings.current().value("showPanel"))
        self._marking_menu = MarkingMenu(self.trigger, self.states)
        self._view_timer   = QtCore.QTimer()
        self._view_timer.timeout.connect(self._marking_menu.hookNewViews)
        self._view_timer.start(_WATCH_INTERVAL)
        settings.current().addListener(self._on_setting_changed)

    def release(self):
        """install で出したものを消す。"""
        settings.current().removeListener(self._on_setting_changed)
        if self._view_timer is not None:
            self._view_timer.stop()
            self._view_timer = None
        if self._marking_menu is not None:
            self._marking_menu.release()
            self._marking_menu = None
        self._show_panel(False)

    def shortcuts(self):
        """ツールのキー -> 呼ぶ関数 (tool.view_input.ViewInputFilter に渡す)。"""
        return {key: self._command(action_id) for key, action_id in KEY_ACTIONS.items()}

    def states(self):
        """操作ごとの (表示名, チェック。チェックの無い操作は None)。パネルのボタンとマーキングメニューの見た目。"""
        values      = settings.current()
        select_tool = self._tool.subTools().get(MODE_SELECT)
        checked     = {mode: mode == self._tool.mode() for mode in MODES}
        checked.update({
            LOOP:       select_tool.loopHighlight() if select_tool is not None else False,
            SYMMETRY:   current_plane() is not None,   # ツールの対称か、Maya の対称が効いているか
            AUTO:       values.value("autoApply"),
            SHOW_PANEL: values.value("showPanel"),
        })
        states = {action[0]: (action[1], checked.get(action[0])) for action in PANEL_ACTIONS if action is not None}
        states[AUTO_OPERATION] = ("自動カット" if values.value("autoOperation") == "cut" else "自動縫合", None)
        states[SHOW_PANEL]     = ("パネルを表示", checked[SHOW_PANEL])
        states[DELETE_ON_COMPLETE] = ("確定後にガイドを削除", values.value("deleteGuideOnComplete"))
        states[SPLIT]          = ("切り離す", None)
        states[JOIN]           = ("接続する", None)
        for action_id, (key, value, label) in SET_SETTINGS.items():
            states[action_id] = (label, values.value(key) == value)

        return states

    def sync(self):
        """パネルのボタンの見た目を、今の状態に合わせる (モードを替えたときなど)。"""
        if self._panel is None:
            return

        states = self.states()
        for action in PANEL_ACTIONS:   # パネルにあるボタンだけ (メニューだけの操作は states にあってもボタンが無い)
            if action is not None and states[action[0]][1] is not None:
                self._panel.setChecked(action[0], states[action[0]][1])

        operation = settings.current().value("autoOperation")   # "cut" / "sew" (ui.icons の名前と同じ)
        self._panel.setAppearance(AUTO_OPERATION, operation, states[AUTO_OPERATION][0])

    def trigger(self, action_id):
        """操作 (actions の ID) を当てる。"""
        sub_tool = self._tool.subTool()
        if sub_tool is None:
            return

        if action_id == TOGGLE_MODE:
            action_id = MODES[(MODES.index(self._tool.mode()) + 1) % len(MODES)]   # 作成 -> 編集 -> 選択 -> 作成

        if action_id in _TOGGLE_SETTINGS:
            # 設定を切り替える (_on_setting_changed が知らせ・パネルの見た目・出し入れを合わせる)
            key    = _TOGGLE_SETTINGS[action_id]
            values = settings.current()
            values.setValue(key, not values.value(key))
            if action_id == SYMMETRY and current_plane() is not None and current_plane().from_maya:
                log.info("Maya の対称がオンなので、ツールの設定によらず Maya の対称が効きます")
            return

        if action_id in SET_SETTINGS:
            key, value, _ = SET_SETTINGS[action_id]
            settings.current().setValue(key, value)
            if key.startswith("mirror") and current_plane() is not None and current_plane().from_maya:
                log.info("Maya の対称がオンなので、Maya の空間・軸が効きます")
            return

        if action_id == AUTO_OPERATION:
            values = settings.current()
            values.setValue("autoOperation", "sew" if values.value("autoOperation") == "cut" else "cut")
            return

        if action_id == LOOP:
            # ループの事前ハイライトを切り替える。オンにしたら選択のモードにする (選択のモードの補助なので)
            select_tool = self._tool.subTools()[MODE_SELECT]
            select_tool.setLoopHighlight(not select_tool.loopHighlight())
            if select_tool.loopHighlight() and self._tool.mode() != MODE_SELECT:
                self._tool.setMode(MODE_SELECT)
            self.sync()
            view.refresh()
            return

        if action_id == DELETE_ALL:
            guide_cleanup.delete_target_guides(self._tool.targets())
            return

        if action_id in (SPLIT, JOIN):
            if action_id == SPLIT:
                sub_tool.splitPoints()   # 編集のモードだけが受け取る
            else:
                sub_tool.joinGuides()
            view.refresh()
            return

        if action_id in MODES:
            self._tool.setMode(action_id)
        else:
            sub_tool.applyOperation(action_id)   # カット / 縫合
            view.refresh()

    # -- 非公開メソッド -------------------------------------------------------
    def _command(self, action_id):
        return lambda: self.trigger(action_id)

    def _show_panel(self, visible):
        # ビューのパネルを出す / 消す (設定 showPanel)
        if visible and self._panel is None:
            self._panel = panel_host.open_panel(self.trigger)
            self.sync()
        elif not visible and self._panel is not None:
            panel_host.close_panel(self._panel)
            self._panel = None

    def _on_setting_changed(self, key):
        # 設定が変わった (色は描くたびに引くので、描き直すだけ)。ツール設定のウィンドウの値も入れ直す
        tool_settings_window.refresh()
        if key in ("symmetry", "mirrorSpace", "mirrorAxis", "mirrorTolerance"):
            self._report_symmetry()
        if key in ("autoApply", "autoOperation", "deleteGuideOnComplete"):
            self._report_auto()
        if key == "straightness":
            self._apply_straightness()
        if key == "showPanel":
            self._show_panel(settings.current().value("showPanel"))
        self.sync()
        view.refresh()

    def _apply_straightness(self):
        # まっすぐさの重みを今のグラフに入れ、サブツールに知らせる (プレビューなどの木を作り直させる)。
        # 今あるガイドの区間は変えない (区間は求めた頂点の列を持っているので、次に求める所から効く)
        if self._tool.targets() is None:
            return

        for target in self._tool.targets():
            target.graph().setTurnWeight(settings.current().value("straightness"))
        for sub_tool in self._tool.subTools().values():
            sub_tool.targetChanged()

    def _report_auto(self):
        values = settings.current()
        if values.value("autoApply"):
            log.info("自動: 作成のモードで点を足すたびに{}します".format(
                "カット" if values.value("autoOperation") == "cut" else "縫合"))
        else:
            log.info("自動: オフ (C / S でカット / 縫合)")
        if values.value("deleteGuideOnComplete"):
            log.info("確定したガイドは、確定と同時に削除します (UV のカット / 縫合は残ります)")

    def _report_symmetry(self):
        # 今の対称をログに出し、対応表を先に作る (反対側が見つからない頂点があれば TargetMesh.mirrorMap が知らせる)
        plane = current_plane()
        log.info(describe(plane))
        if plane is not None and self._tool.targets() is not None:
            for target in self._tool.targets():
                target.mirrorMap(plane)
