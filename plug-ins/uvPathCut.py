# -*- coding: utf-8 -*-
"""
UV パスカットのプラグイン (登録だけ)。中身は scripts/UVPathCut パッケージ。

    cmds.loadPlugin("uvPathCut")    # または  import UVPathCut; UVPathCut.tool()

仕組み:
- Maya はプラグインのファイルを名前の無い名前空間で実行し、initializePlugin で登録する。
  このファイルには登録の処理だけを書き、ツールの中身はパッケージに置く
  (パッケージは scripts/ が PYTHONPATH にあれば import できる。起動用のバッチが足している)
- 登録する creator は、パッケージのクラスを「呼ばれるたびに」importlib で引いて作る。
  クラスそのものを登録すると、パッケージをリロードしても登録したときの古いクラスが使われ
  続けるため (mayakit_attribute.py と同じ方式)。リロードは UVPathCut.reloader.reload_modules()
- コマンドの名前は UVPathCut.constants から読む (パッケージの側も同じ名前で呼ぶため)
- マニピュレータはノードとして registerNode で登録する (種類は kManipulatorNode)。
  creator / initialize もパッケージのクラスを毎回引く
"""
import importlib

import maya.api.OpenMaya as om

_VENDOR = "MayaPy"
_VERSION = "2.0"
_CONTEXT_MODULE = "UVPathCut.tool.context"
_MANIP_MODULE = "UVPathCut.tool.manipulator"
_EDIT_MODULE = "UVPathCut.scene.edit"


def maya_useNewAPI():
    """この関数があると、Maya はこのプラグインを API 2.0 (maya.api.OpenMaya) として扱う。"""
    pass


def _context_module():
    return importlib.import_module(_CONTEXT_MODULE)


def _create_context_command():
    return _context_module().UVPathCutContextCommand()


def _create_tool_command():
    return _context_module().ToolCommand()


def _create_manip():
    return importlib.import_module(_MANIP_MODULE).UVPathManip()


def _initialize_manip():
    importlib.import_module(_MANIP_MODULE).UVPathManip.initialize()


def _create_edit_command():
    return importlib.import_module(_EDIT_MODULE).PathEditCommand()


def _edit_syntax():
    return importlib.import_module(_EDIT_MODULE).PathEditCommand.syntax()


def _constants():
    try:
        return importlib.import_module("UVPathCut.constants")
    except ImportError:
        raise RuntimeError("UVPathCut パッケージが見つかりません。scripts/ を PYTHONPATH に"
                           "足してください (起動用のバッチ maya20XX.bat が足します)")


def initializePlugin(plugin):
    """loadPlugin のときに 1 回呼ばれる。"""
    names = _constants()
    _context_module()   # 読めることを先に確かめる (失敗したら登録しない)
    fn = om.MFnPlugin(plugin, _VENDOR, _VERSION, "Any")
    fn.registerNode(names.MANIP_NODE, om.MTypeId(names.MANIP_TYPE_ID), _create_manip,
                    _initialize_manip, om.MPxNode.kManipulatorNode)
    fn.registerContextCommand(names.CONTEXT_COMMAND, _create_context_command)
    fn.registerCommand(names.TOOL_COMMAND, _create_tool_command)
    fn.registerCommand(names.EDIT_COMMAND, _create_edit_command, _edit_syntax)


def uninitializePlugin(plugin):
    """unloadPlugin のときに 1 回呼ばれる。"""
    names = _constants()
    _context_module().delete_tool_context()   # 登録を外す前に、このツールのコンテキストを消す
    fn = om.MFnPlugin(plugin)
    fn.deregisterCommand(names.EDIT_COMMAND)
    fn.deregisterCommand(names.TOOL_COMMAND)
    fn.deregisterContextCommand(names.CONTEXT_COMMAND)
    fn.deregisterNode(om.MTypeId(names.MANIP_TYPE_ID))
