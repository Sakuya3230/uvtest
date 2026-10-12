# -*- coding: utf-8 -*-
"""
UVPathCut の公開 API。

    import UVPathCut
    UVPathCut.tool()            # プラグインを読み込んで、このツールにする
    UVPathCut.load_plugin()     # プラグインを読み込むだけ
    UVPathCut.reload_modules()  # reloader を読み直してから、全モジュールをリロードする
    UVPathCut.reload_plugin()   # プラグインを読み直す (コマンド・ノードを足したとき)

maya はここでは import しない (関数を呼んだときに読む)。
"""
import os

from .constants import PLUGIN_COMMANDS, PLUGIN_NAME, PLUGIN_NODES, TOOL_COMMAND

__all__ = ["diagnose_ring", "tool", "load_plugin", "plugin_path", "reload_modules", "reload_plugin",
           "missing_registrations", "ensure_plugin_current"]


def plugin_path():
    """プラグインのファイルのフルパス (scripts/UVPathCut から見た ../../plug-ins/uvPathCut.py)。"""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", "plug-ins", PLUGIN_NAME + ".py"))


def load_plugin():
    """プラグインが読み込まれていなければ読み込む。読み込まれていれば何もしない。

    起動用のバッチが plug-ins/ を MAYA_PLUG_IN_PATH に足していれば名前で読める。
    足していなければ、このパッケージの場所からのフルパスで読む。
    """
    import maya.cmds as cmds
    if cmds.pluginInfo(PLUGIN_NAME, query=True, loaded=True):
        return
    try:
        cmds.loadPlugin(PLUGIN_NAME + ".py", quiet=True)
    except RuntimeError:
        cmds.loadPlugin(plugin_path(), quiet=True)


def tool():
    """プラグインを読み込んで、このツールにする。コンテキストの名前を返す。"""
    import maya.cmds as cmds
    load_plugin()
    return getattr(cmds, TOOL_COMMAND)()


def reload_modules():
    """reloader 自身を読み直してから、全モジュールを依存順にリロードする。

    reloader.reload().reload_modules() と同じ (ツールのコンテキストも消す)。
    """
    from . import reloader
    return reloader.reload().reload_modules()


def missing_registrations():
    """読み込み済みのプラグインに足りないコマンド・ノードの名前のリスト (読み込まれていなければ None)。

    コマンドは maya.cmds の属性になっているかで確かめる (登録すると増え、外すと消える。
    pluginInfo -command にはコンテキストのコマンドが出ないので使わない)。ノードは pluginInfo -dependNode。
    """
    import maya.cmds as cmds
    if not cmds.pluginInfo(PLUGIN_NAME, query=True, loaded=True):
        return None
    nodes = cmds.pluginInfo(PLUGIN_NAME, query=True, dependNode=True) or []
    missing = [name for name in PLUGIN_COMMANDS if not hasattr(cmds, name)]
    missing += [name for name in PLUGIN_NODES if name not in nodes]
    return missing


def reload_plugin():
    """プラグインを読み直す (コマンド・ノードの登録をやり直す)。

    先にツールのコンテキストを消し、Undo の履歴を消す (cmds.flushUndo)。プラグインのコマンドが
    Undo のキューに残っていると、プラグインを外せないため。
    """
    import maya.cmds as cmds
    from .tool.context import delete_tool_context
    if cmds.pluginInfo(PLUGIN_NAME, query=True, loaded=True):
        delete_tool_context()
        cmds.flushUndo()
        cmds.unloadPlugin(PLUGIN_NAME)
    load_plugin()


def ensure_plugin_current():
    """読み込み済みのプラグインに足りない登録があれば、読み直す。足りなかった名前のリストを返す。

    reloader.reload_modules の最後に呼ぶ。読み込まれていなければ何もしない (tool() が読む)。
    """
    from . import log
    missing = missing_registrations()
    if not missing:
        return []
    log.info("プラグインに {} が登録されていないので、読み直します "
             "(Undo の履歴は消えます)".format(", ".join(missing)))
    reload_plugin()
    return missing


def diagnose_ring(start=None, end=None):
    """(調べる用) 輪切りの各段階の数を出す (tool.ring.diagnose)。GUI で、メッシュを選んでから呼ぶ。"""
    from .tool.ring import diagnose
    diagnose(start, end)
