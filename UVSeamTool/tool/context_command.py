"""
コンテキストを作るコマンド (uvSeamToolCtx) と、コンテキストを消す関数。
"""

import maya.api.OpenMayaUI as omui
import maya.cmds as cmds

from ..constants import CONTEXT_NAME


class UVSeamToolContextCommand(omui.MPxContextCommand):
    """`cmds.uvSeamToolCtx("名前")` で UVSeamToolContext を作るコマンド。"""

    # -- 上書きするメソッド (MPxContextCommand) -------------------------------
    def makeObj(self):
        # 呼ぶときに引く (リロードのあとは新しいクラスで作る)
        from .context import UVSeamToolContext

        return UVSeamToolContext()


def delete_tool_context():
    """このツールのコンテキストを消す (使っていたら選択ツールに戻してから)。

    コンテキストは作ったときのクラスのままなので、リロードの前に消して作り直さないと古いコードが動き続ける。
    """
    if not cmds.contextInfo(CONTEXT_NAME, exists=True):
        return

    if cmds.currentCtx() == CONTEXT_NAME:
        cmds.setToolTo("selectSuperContext")

    cmds.deleteUI(CONTEXT_NAME, toolContext=True)
