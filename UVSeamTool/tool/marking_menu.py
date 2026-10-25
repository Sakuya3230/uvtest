"""
ツールのラジアルメニュー (Maya のマーキングメニュー。ビューで Shift+右クリック)。
"""

import maya.cmds as cmds
import maya.mel as mel

from ..utils import log
from .actions import MARKING_MENU

# ビュー (modelPanel) の Shift+右クリックのマーキングメニューは、Maya の ModelEdMenu.mel が作る
# "<パネル>CommandPop" (中身は開くたびに MEL の contextToolsMM "<メニューのフルパス>" が作る)
_POPUP_SUFFIX   = "CommandPop"
_ORIGINAL_MEL   = 'contextToolsMM "{}"'


class MarkingMenu:
    """ツールを使っている間だけ、ビューの Shift+右クリックをツールのマーキングメニューにする。

    Shift+右クリックのメニューは、各ビューの Maya の標準のメニュー (<パネル>CommandPop) が出す (別のメニューを
    viewPanes に付けても、標準のメニューが先に出た)。そこで標準のメニューの中身を作る関数 (postMenuCommand) を、
    ツールの間だけツールの項目を作る関数に差し替え、抜けるときに Maya と同じ MEL のコマンドに戻す
    (postMenuCommand は問い合わせできないので、元のコマンドは ModelEdMenu.mel と同じ形で組み立てる。
    cmds に文字列を渡すと Python のコードとして扱われるので、戻すのは MEL の popupMenu -edit で)。
    項目と置き場所は actions.MARKING_MENU の表、表示名とチェックは state() ({ID: (表示名, チェック。無ければ None)})
    から引き、選んだら on_action(ID) を呼ぶ (パネルのボタン・キーと同じ)。
    ツールを使っている間に新しくできたビュー (切り離したパネル・初めて表示したビューなど) のメニューは、
    hookNewViews (ToolActions が見回りで呼ぶ) で差し替える。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, on_action, state):
        self._on_action = on_action
        self._state     = state
        self._popups    = []            # 差し替えたメニュー (フルパス)

        self.hookNewViews()
        if not self._popups and not cmds.about(batch=True):
            log.warning("ビューの Shift+右クリックのメニューが見つからないので、マーキングメニューを付けられません")

    # -- 公開メソッド ---------------------------------------------------------
    def hookNewViews(self):
        """まだ差し替えていないビューのメニューを差し替える (ツールを使い始めたとき・見回りのたび)。"""
        for popup in _view_popups():
            if popup in self._popups:
                continue

            try:
                cmds.popupMenu(popup, edit=True, postMenuCommand=self._post_command(popup))
            except RuntimeError as error:
                log.debug("{}: 差し替えられません ({})".format(popup, error))
                continue
            self._popups.append(popup)
            log.debug("{}: Shift+右クリックのメニューを差し替えました".format(popup))

    def release(self):
        """標準のメニューを元に戻す (ツールを抜けるときに必ず呼ぶ。戻さないと、ツールの外でも出る)。"""
        for popup in self._popups:
            if cmds.popupMenu(popup, exists=True):
                _restore(popup)
        self._popups = []

    # -- 非公開メソッド -------------------------------------------------------
    def _post_command(self, popup):
        # メニューを開くたびに呼ばれる関数
        return lambda *args: self._build(popup)

    def _build(self, popup):
        # 項目を消して作り直す (チェックを今の状態に合わせる)。置き場所の無い項目は下のリストに並ぶ
        cmds.popupMenu(popup, edit=True, deleteAllItems=True)
        cmds.setParent(popup, menu=True)
        self._add_items(MARKING_MENU, self._state())
        cmds.menuItem(divider=True)
        cmds.menuItem(label="ツール設定...", command=lambda *args: cmds.toolPropertyWindow())

    def _add_items(self, items, states):
        # 今のメニュー (setParent -menu) に items を足す。3 つ組は子のマーキングメニュー (中へ入って足し、戻る)
        for item in items:
            if len(item) == 3:
                label, position, children = item
                cmds.menuItem(label=label, radialPosition=position, subMenu=True)
                self._add_items(children, states)
                cmds.setParent("..", menu=True)
                continue

            action_id, position = item
            label, checked      = states[action_id]
            options             = {"radialPosition": position} if position else {}
            if checked is not None:
                options["checkBox"] = checked
            cmds.menuItem(label=label, command=self._command(action_id), **options)

    def _command(self, action_id):
        # menuItem の command (チェックの項目は bool を渡してくるので、引数は使わない)
        return lambda *args: self._on_action(action_id)


def _restore(popup):
    # postMenuCommand を Maya と同じ MEL のコマンドに戻す (MEL から設定しないと MEL として呼ばれない)
    command = _ORIGINAL_MEL.format(popup).replace('"', '\\"')
    mel.eval('popupMenu -edit -postMenuCommand "{}" "{}";'.format(command, popup))


def _view_popups():
    # ビュー (modelPanel) の Shift+右クリックのマーキングメニューの名前 (フルパス)
    return [name for name in cmds.lsUI(type="popupMenu", long=True) or [] if name.endswith(_POPUP_SUFFIX)]
