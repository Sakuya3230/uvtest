"""
ツールのコンテキスト。マウスとキーを今のサブツールへ渡すだけ。
"""

import maya.api.OpenMayaUI as omui

from ..compat import accel
from ..constants import TOOL_CLASS
from ..core.guide import guide_store
from ..utils import log, view
from ..utils.selection import enter_edge_mode, selected_meshes
from . import exit_selection, mesh_checks, tool_settings_window
from .actions import HELP_TEXTS, MODE_CREATE, MODE_EDIT, MODE_SELECT
from .create_tool import CreateTool
from .edit_tool import EditTool
from .painter import Painter
from .select_tool import SelectTool
from .target_watch import TargetWatch
from .targets import Targets
from .tool_actions import ToolActions
from .view_input import ViewInputFilter


class UVSeamToolContext(omui.MPxContext):
    """UVSeamTool のコンテキスト。

    自分では判断せず、今のサブツール (tool.sub_tool.SubTool) のメソッドを呼ぶ。
    選択はサブツールが自前で行うので、基底は MPxContext (Maya の選択の働きを持たない)。サブツールが受け取らなかった
    マウスの操作は何もしない。
    描画は drawFeedback (ビューを描き直すたびに Maya が呼ぶ) で、サブツールに Painter を渡して描かせる。
    ガイドの組が変わったら (Undo / Redo でも)、サブツールに知らせて描き直す。
    モード (作成 / 編集 / 選択) を替えると、今のサブツールを入れ替える。
    ほかの役目は分けてある: 対象のメッシュの見張りは tool.target_watch.TargetWatch、パネルのボタン・キー・
    マーキングメニューの操作と設定の変更は tool.tool_actions.ToolActions。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self):
        super().__init__()
        self.setTitleString("UV シームツール")

        self._sub_tools     = {}        # モード -> サブツール (ツールを有効にしている間だけ)
        self._mode          = MODE_CREATE
        self._sub_tool      = None      # 今のモードのサブツール
        self._consumed      = False     # 今のマウスの操作 (押してから離すまで) をサブツールが受け取ったか
        self._targets       = None      # tool.targets.Targets (ツールを有効にしている間だけ)
        self._watch         = None      # TargetWatch (ツールを有効にしている間だけ)
        self._actions       = ToolActions(self)
        self._view_input    = None      # ViewInputFilter (ツールを有効にしている間だけ)

    # -- 上書きするメソッド (MPxContext) --------------------------------------
    def stringClassName(self):
        # Maya はこの名前に Properties / Values を付けた MEL の global proc で、ツール設定のウィンドウを作る
        return TOOL_CLASS

    def toolOnSetup(self, event):
        # ツールが有効になった。基底の toolOnSetup は呼ばない (API 2.0 では SystemError になる)
        # 片付けは toolOffCleanup が、ここで付けたものを逆の順に外す

        # 1. 使えるかを確かめる (ツール設定のウィンドウの入り口は、リロードのあとも定義し直す)
        tool_settings_window.define()
        try:
            accel.require()
        except RuntimeError as error:
            log.warning(str(error))
            return

        meshes = selected_meshes()
        if not meshes:
            log.warning("メッシュを選んでからツールにしてください")
            return

        # 2. 対象のメッシュ (エッジの選択モードにする。扱えないメッシュは知らせる) と、その見張り
        targets = Targets(meshes)
        enter_edge_mode(meshes)
        for mesh in meshes:
            mesh_checks.report(mesh)
        self._targets   = targets
        self._watch     = TargetWatch(targets, self._on_targets_changed)

        # 3. サブツール (作成で始める)
        self._sub_tools = {MODE_CREATE: CreateTool(targets), MODE_EDIT: EditTool(targets),
                           MODE_SELECT: SelectTool(targets)}
        self.setMode(MODE_CREATE)

        # 4. ガイドの組が変わったら描き直す (Undo / Redo でも)
        guide_store.store().addListener(self._on_guides_changed)

        # 5. コンテキストのメソッドでは受け取れない入力 (右クリック・ダブルクリック・ドラッグ中の Esc・キー) と、
        #    パネル・マーキングメニュー・設定の変更 (ToolActions)
        self._view_input = ViewInputFilter(self._on_right_click, self._on_double_click, self._is_busy, self._on_cancel,
                                           self._actions.shortcuts(), self._on_wheel)
        self._view_input.install()
        self._actions.install()

        view.refresh()
        log.debug("ツールを有効にしました ({})".format(", ".join(mesh.name() for mesh in meshes)))

    def toolOffCleanup(self):
        # ツールが無効になった。toolOnSetup で付けたものを逆の順に外す。基底の toolOffCleanup も呼ばない
        # (コールバック・フィルターを外し忘れると、ツールを抜けても・リロードしたあとも古いコードが呼ばれる)

        # 3. サブツール (作成中のガイドがあれば、ここで確定する)。作成・編集なら、ガイドのエッジを選んで抜ける
        if self._sub_tool is not None:
            self._sub_tool.deactivate()
            if self._mode != MODE_SELECT:
                exit_selection.select_guides(self._targets)

        # 5. 入力のフィルター・パネル・マーキングメニュー・設定の変更
        if self._view_input is not None:
            self._view_input.uninstall()
            self._view_input = None
            self._actions.release()

        # 4. ガイドの組のリスナー
        guide_store.store().removeListener(self._on_guides_changed)

        # 2. 見張りと対象のメッシュ
        if self._watch is not None:
            self._watch.release()
            self._watch = None

        self._sub_tool  = None
        self._sub_tools = {}
        self._targets   = None

        view.refresh()   # 描いていたものを消す
        log.debug("ツールを無効にしました")

    def doPtrMoved(self, event, draw_manager, frame_context):
        # ボタンを押さずにマウスを動かした (ホバー)
        if self._sub_tool is None:
            return

        x, y = event.position
        if self._sub_tool.hover(x, y):
            view.refresh()

    def drawFeedback(self, *args):
        # ビューを描き直すたびに呼ばれる。引数は (drawMgr, frameContext) (スタブには event もあるので後ろの 2 つ)
        if self._sub_tool is not None:
            self._sub_tool.draw(Painter(args[-2], args[-1]))

    def doPress(self, event, draw_manager, frame_context):
        # 受け取らなかった操作 (左ボタン以外など) は何もしない (Maya の選択は使わない)
        x, y = event.position
        self._consumed = self._sub_tool is not None and self._sub_tool.press(
            x, y, event.mouseButton(), event.isModifierShift(), event.isModifierControl())
        view.refresh()   # 受け取らなくても、サブツールの状態 (選択など) が変わっていることがある

    def doDrag(self, event, draw_manager, frame_context):
        if self._consumed:
            x, y = event.position
            if self._sub_tool.drag(x, y):
                view.refresh()

    def doRelease(self, event, draw_manager, frame_context):
        if self._consumed:
            self._consumed = False
            x, y = event.position
            self._sub_tool.release(x, y)
            view.refresh()

    def completeAction(self):
        if self._sub_tool is not None:
            self._sub_tool.complete()
            view.refresh()

    def abortAction(self):
        if self._sub_tool is not None:
            self._sub_tool.abort()
            view.refresh()

    def deleteAction(self):
        if self._sub_tool is not None:
            self._sub_tool.delete()
            view.refresh()

    # -- 公開メソッド (ToolActions から使う) -----------------------------------
    def mode(self):
        return self._mode

    def setMode(self, mode):
        """今のサブツールを入れ替える。"""
        if self._sub_tool is not None:
            self._sub_tool.deactivate()

        self._mode     = mode
        self._sub_tool = self._sub_tools[mode]
        self._sub_tool.activate()
        self.setHelpString(HELP_TEXTS[mode])
        self._actions.sync()
        view.refresh()
        log.debug("モード: {}".format(mode))

    def subTool(self):
        """今のモードのサブツール (ツールを有効にしていなければ None)。"""
        return self._sub_tool

    def subTools(self):
        """モード -> サブツール (ツールを有効にしていなければ空)。"""
        return self._sub_tools

    def targets(self):
        """対象のメッシュ (tool.targets.Targets。ツールを有効にしていなければ None)。"""
        return self._targets

    # -- 非公開メソッド -------------------------------------------------------
    def _on_right_click(self):
        # ビューで右クリック (ViewInputFilter から)。受け取ったら True
        return self._sub_tool is not None and self._sub_tool.rightClick()

    def _on_double_click(self, x, y, shift, ctrl):
        # ビューで左ボタンをダブルクリック (ViewInputFilter から)。受け取ったら True
        if self._sub_tool is None or not self._sub_tool.doubleClick(x, y, shift, ctrl):
            return False

        view.refresh()

        return True

    def _on_wheel(self, steps, shift, ctrl):
        # ビューで Shift / Ctrl を押しながらホイール (ViewInputFilter から)。受け取ったら True
        if self._sub_tool is None or not self._sub_tool.wheel(steps, shift, ctrl):
            return False

        view.refresh()

        return True

    def _is_busy(self):
        return self._sub_tool is not None and self._sub_tool.isBusy()

    def _on_cancel(self):
        # ドラッグ中の Esc (ViewInputFilter から。マウスを押している間は abortAction が呼ばれないため)
        self._sub_tool.cancel()
        view.refresh()

    def _on_targets_changed(self):
        # 対象のメッシュが変わった (TargetWatch から。読み直した・外した)。サブツールに知らせる
        for sub_tool in self._sub_tools.values():
            sub_tool.targetChanged()

    def _on_guides_changed(self, key):
        # ガイドの組が変わった (このツールの操作でも、Undo / Redo でも)
        if self._sub_tool is not None:
            self._sub_tool.refresh()

        view.refresh()
