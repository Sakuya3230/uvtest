"""
UVSeamTool のプラグイン (登録だけ)。中身は scripts/UVSeamTool パッケージ。

    import UVSeamTool; UVSeamTool.tool()

creator は、パッケージのクラスを呼ばれるたびに importlib で引いて作る。クラスそのものを登録すると、
パッケージをリロードしても登録したときの古いクラスが使われ続けるため。
"""

import importlib

import maya.api.OpenMaya as om

_COMMAND_MODULE = "UVSeamTool.tool.context_command"
_UNDO_MODULE    = "UVSeamTool.utils.undo"


def maya_useNewAPI():
    """この関数があると、Maya はこのプラグインを API 2.0 (maya.api.OpenMaya) として扱う。"""
    pass


def _constants():
    return importlib.import_module("UVSeamTool.constants")


def _create_context_command():
    return importlib.import_module(_COMMAND_MODULE).UVSeamToolContextCommand()


def _create_undo_command():
    return importlib.import_module(_UNDO_MODULE).UndoCommand()


def initializePlugin(plugin):
    fn = om.MFnPlugin(plugin, "MayaPy", "0.1", "Any")
    fn.registerContextCommand(_constants().CONTEXT_COMMAND, _create_context_command)
    fn.registerCommand(_constants().EDIT_COMMAND, _create_undo_command)


def uninitializePlugin(plugin):
    importlib.import_module(_COMMAND_MODULE).delete_tool_context()
    fn = om.MFnPlugin(plugin)
    fn.deregisterCommand(_constants().EDIT_COMMAND)
    fn.deregisterContextCommand(_constants().CONTEXT_COMMAND)
