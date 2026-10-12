# -*- coding: utf-8 -*-
"""
UVPathCut のモジュールを依存順に import / リロードする。

    import UVPathCut.reloader as r; r.reload().reload_modules()
    import UVPathCut; UVPathCut.tool()

reload() はこの reloader 自身を読み直して、読み直したモジュールを返す。
import UVPathCut.reloader は読み込み済みの古いモジュールを返すので、そのまま reload_modules()
を呼ぶと、MODULES に足した新しいモジュールがリロードされない (段階 3 で、リロードのあとに
古いモジュールが残った)。返ってきた新しい reloader の reload_modules() を呼べば、いつも
ファイルにある新しい一覧でリロードされる (AttributeInspector の reloader と同じ形)。

reload_modules() の流れ:
1. ツールのコンテキストを消す (コンテキストのインスタンスは作ったときのクラスのままなので、
   消さないと古いコードが動き続ける)
2. MODULES -> MAYA_MODULES の順に読み直す (読み込まれていなければ import)
3. 一覧に無いのに読み込まれている UVPathCut のモジュール (= 読み直していないもの) があれば知らせる
4. 読み込み済みのプラグインに、constants.PLUGIN_COMMANDS / PLUGIN_NODES がそろっているかを確かめ、
   足りなければプラグインを読み直す (api.ensure_plugin_current。Undo の履歴は消える)
プラグインは普段は読み直さなくてよい (プラグインの creator がモジュールを毎回引くので、
次に作るものは新しいクラスになる)。ただし、コマンド・ノードの登録はプラグインを読み込んだときに
しか行われないので、コマンド・ノードを足したとき (段階 8 の uvPathCutEdit) は 4 が要る。

モジュールを追加したら MODULES の正しい位置に足すこと
(tests/UVPathCut/test_dependencies.py が漏れを検出する)。
"""
import importlib
import sys

__all__ = ["MODULES", "MAYA_MODULES", "reload", "reload_modules", "reload_module"]

# Maya に依存しないもの (依存の浅い順)
MODULES = [
    "UVPathCut.constants",
    "UVPathCut.log",
    "UVPathCut.core",
    "UVPathCut.core.settings",
    "UVPathCut.core.geometry",
    "UVPathCut.core.picking",
    "UVPathCut.core.accel",
    "UVPathCut.core.graph",
    "UVPathCut.core.path",
    "UVPathCut.core.turning",
    "UVPathCut.core.draw_list",
    "UVPathCut.core.session",
    "UVPathCut.core.sync",
    "UVPathCut.core.selection",
    "UVPathCut.core.ring",
    "UVPathCut.core.section",
    "UVPathCut.core.mirror",
    "UVPathCut.core.components",
    "UVPathCut.core.actions",
    "UVPathCut.core.panel",
    "UVPathCut.core.tool_ui_text",
]

# Maya が要るもの (Maya の中でだけリロードする)
MAYA_MODULES = [
    "UVPathCut.scene",
    "UVPathCut.scene.prefs",
    "UVPathCut.scene.mesh",
    "UVPathCut.scene.mirror",
    "UVPathCut.scene.selection",
    "UVPathCut.scene.ring",
    "UVPathCut.scene.targets",
    "UVPathCut.scene.edit",
    "UVPathCut.tool",
    "UVPathCut.tool.drawing",
    "UVPathCut.tool.manipulator",
    "UVPathCut.tool.keys",
    "UVPathCut.tool.tool_ui",
    "UVPathCut.tool.selecting",
    "UVPathCut.tool.symmetry",
    "UVPathCut.tool.ring",
    "UVPathCut.tool.command",
    "UVPathCut.tool.context",
    "UVPathCut.api",
    "UVPathCut",
]


def _has_maya():
    try:
        importlib.import_module("maya.cmds")
        return True
    except ImportError:
        return False


def reload_module(module_name):
    """モジュールを、読み込まれていればリロード、まだなら import する。そのモジュールを返す。"""
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


def reload():
    """この reloader 自身を読み直して返す。

        r.reload().reload_modules()   # 新しい一覧 (MODULES) でリロードする
    """
    return reload_module(__name__)


def reload_modules():
    """一覧のモジュールを依存順にリロードする (読み込まれていないものは import する)。

    この reloader 自身は読み直さない (先に reload() で読み直してから呼ぶ)。
    読み直したモジュールのリストを返す。
    """
    in_maya = _has_maya()
    if in_maya and "UVPathCut.tool.context" in sys.modules:
        sys.modules["UVPathCut.tool.context"].delete_tool_context()
    names = MODULES + (MAYA_MODULES if in_maya else ["UVPathCut.api", "UVPathCut"])
    modules = [reload_module(name) for name in names]
    unlisted = sorted(name for name in sys.modules
                      if name.startswith("UVPathCut.") and name not in names
                      and name != __name__ and sys.modules[name] is not None)
    if unlisted:
        print("UV パスカット: 一覧 (reloader.MODULES / MAYA_MODULES) に無いので読み直して"
              "いないモジュール: {}".format(", ".join(unlisted)))
    if in_maya:
        sys.modules["UVPathCut.api"].ensure_plugin_current()
    return modules
