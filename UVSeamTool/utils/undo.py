"""
Maya の Undo に載せる (Python の関数の組を、Undo できる 1 回のコマンドにする)。

    undo.run(redo, undo)    redo() をすぐ呼び、Ctrl+Z で undo()、やり直しで redo() を呼ぶ
    with undo.chunk("名前"): ...   中の Maya のコマンド (polyMapCut など) をまとめて 1 回の Undo にする

コマンド (constants.EDIT_COMMAND) はプラグインが登録する。関数はコマンドの引数で渡せないので、
モジュールに置いてからコマンドを呼び、doIt で受け取る。
"""

import contextlib

import maya.api.OpenMaya as om
import maya.cmds as cmds

from ..constants import EDIT_COMMAND

_pending = None   # 次の doIt に渡す (redo, undo)


class UndoCommand(om.MPxCommand):
    """run() が置いた関数の組を持ち、Undo / Redo で呼ぶコマンド。"""

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self):
        super().__init__()

        self._redo  = None
        self._undo  = None

    # -- 上書きするメソッド (MPxCommand) -------------------------------------
    def doIt(self, args):
        if _pending is None:
            raise RuntimeError("{} は utils.undo.run() から呼んでください".format(EDIT_COMMAND))

        self._redo, self._undo = _pending
        self._redo()

    def redoIt(self):
        self._redo()

    def undoIt(self):
        self._undo()

    def isUndoable(self):
        return True


@contextlib.contextmanager
def chunk(name):
    """中で呼んだ Maya のコマンドを、1 回の Undo (名前は name) にまとめる。"""
    cmds.undoInfo(openChunk=True, chunkName=name)
    try:
        yield
    finally:
        cmds.undoInfo(closeChunk=True)


def run(redo, undo):
    """redo() を呼び、Undo の列に (redo, undo) を 1 回分として積む。"""
    global _pending

    _pending = (redo, undo)
    try:
        getattr(cmds, EDIT_COMMAND)()
    finally:
        _pending = None
