"""
開発中のリロード。

MODULES は依存の順 (使われる側が先)。モジュールを足したらここにも足す。

    import UVSeamTool.reloader as r; r.reload().reload_modules()

`reload()` が先にこのモジュール自身を読み直して返すので、MODULES を書き換えたあとでも新しい一覧が使われる
(`r.reload_modules()` だけだと、Maya に残っている古い MODULES を使う)。
"""

import importlib
import sys

MODULES = [
    "UVSeamTool.constants",
    "UVSeamTool.compat.accel",
    "UVSeamTool.compat.qt",
    "UVSeamTool.utils.log",
    "UVSeamTool.utils.node",
    "UVSeamTool.utils.mesh",
    "UVSeamTool.utils.selection",
    "UVSeamTool.utils.mesh_watcher",
    "UVSeamTool.utils.selection_watcher",
    "UVSeamTool.utils.symmetry",
    "UVSeamTool.utils.view",
    "UVSeamTool.utils.picking",
    "UVSeamTool.utils.uv_editor",
    "UVSeamTool.utils.undo",
    "UVSeamTool.utils.guide_attribute",
    "UVSeamTool.core.path.mesh_graph",
    "UVSeamTool.core.path.path_tree",
    "UVSeamTool.core.path.turn_path_tree",
    "UVSeamTool.core.path.path_trees",
    "UVSeamTool.core.path.shortest_path",
    "UVSeamTool.core.path.path_preview",
    "UVSeamTool.core.path.topology",
    "UVSeamTool.core.path.edge_topology",
    "UVSeamTool.core.guide.guide_point",
    "UVSeamTool.core.guide.guide_segment",
    "UVSeamTool.core.guide.guide",
    "UVSeamTool.core.guide.solvers",
    "UVSeamTool.core.guide.editing",
    "UVSeamTool.core.guide.guide_set",
    "UVSeamTool.core.guide.segment_modes",
    "UVSeamTool.core.guide.set_editing",
    "UVSeamTool.core.guide.split_join",
    "UVSeamTool.core.guide.group_drag",
    "UVSeamTool.core.guide.guide_store",
    "UVSeamTool.core.guide.guide_json",
    "UVSeamTool.core.guide.guide_picking",
    "UVSeamTool.core.guide.point_drag",
    "UVSeamTool.core.seam.seam",
    "UVSeamTool.core.seam.uv_seams",
    "UVSeamTool.core.settings.setting",
    "UVSeamTool.core.settings.definitions",
    "UVSeamTool.core.settings.json_storage",
    "UVSeamTool.core.settings.settings",
    "UVSeamTool.core.symmetry.mirror_map",
    "UVSeamTool.core.symmetry.guide_mirror",
    "UVSeamTool.ui.icons",
    "UVSeamTool.ui.round_button",
    "UVSeamTool.ui.panel_separator",
    "UVSeamTool.ui.view_panel",
    "UVSeamTool.ui.panel_follower",
    "UVSeamTool.tool.painter",
    "UVSeamTool.tool.symmetry",
    "UVSeamTool.tool.mesh_checks",
    "UVSeamTool.tool.uv_apply",
    "UVSeamTool.tool.actions",
    "UVSeamTool.tool.guide_storage",
    "UVSeamTool.tool.target_mesh",
    "UVSeamTool.tool.targets",
    "UVSeamTool.tool.guide_drawing",
    "UVSeamTool.tool.panel_host",
    "UVSeamTool.tool.setting_controls",
    "UVSeamTool.tool.view_input",
    "UVSeamTool.tool.sub_tool",
    "UVSeamTool.tool.guide_edit",
    "UVSeamTool.tool.guide_cleanup",
    "UVSeamTool.tool.tool_settings_window",
    "UVSeamTool.tool.auto_apply",
    "UVSeamTool.tool.exit_selection",
    "UVSeamTool.tool.edit_operations",
    "UVSeamTool.tool.edit_picker",
    "UVSeamTool.tool.point_dragging",
    "UVSeamTool.tool.create_tool",
    "UVSeamTool.tool.edit_tool",
    "UVSeamTool.tool.select_picker",
    "UVSeamTool.tool.select_tool",
    "UVSeamTool.tool.marking_menu",
    "UVSeamTool.tool.target_watch",
    "UVSeamTool.tool.tool_actions",
    "UVSeamTool.tool.context",
    "UVSeamTool.tool.context_command",
    "UVSeamTool.api",
    "UVSeamTool",
]


def reload():
    """このモジュール自身を読み直して返す。"""
    return importlib.reload(sys.modules[__name__])


def reload_modules():
    """ツールのコンテキストを消してから、MODULES を順に読み直す (まだ読み込んでいないものは読み込む)。

    Undo の履歴も消す。履歴のコマンドは古いモジュールのガイドの置き場所を指していて、リロードのあとに戻すと
    新しい置き場所とずれるため (リロードすると、ガイドの置き場所も空になる)。
    """
    _delete_tool_context()
    _flush_undo()
    _forget_removed_modules()

    for name in MODULES:
        if name in sys.modules:
            importlib.reload(sys.modules[name])
        else:
            importlib.import_module(name)


def _delete_tool_context():
    # コンテキストは作ったときのクラスのまま動くので、消しておく (次の UVSeamTool.tool() で新しいクラスで作る)
    module = sys.modules.get("UVSeamTool.tool.context_command")
    if module is not None:
        module.delete_tool_context()


def _flush_undo():
    if "maya.cmds" in sys.modules:
        sys.modules["maya.cmds"].flushUndo()


def _forget_removed_modules():
    # 一覧から外したモジュール (消したファイル) を sys.modules から外す。残すと古いものが使われ続ける
    keep = set(MODULES) | {__name__}
    for name in list(sys.modules):
        if name.startswith("UVSeamTool.") and name not in keep and not _is_package(name):
            del sys.modules[name]


def _is_package(name):
    return hasattr(sys.modules[name], "__path__")
