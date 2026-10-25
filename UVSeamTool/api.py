"""
公開の入り口。

    import UVSeamTool
    UVSeamTool.tool()                       # メッシュを選んでから。プラグインを読み込んで、このツールにする
    UVSeamTool.cut_guides()                 # 選んでいるメッシュの、保存した確定したガイドでカットする (sew_guides で縫合)
    UVSeamTool.cut_path([0, 105, 210])      # UI なしで (段階 1)

    UVSeamTool.list_guides()                # ガイドを保存しているメッシュの一覧
    UVSeamTool.delete_guides()              # 選んでいるメッシュに保存したガイドを消す (Ctrl+Z で戻る)
    UVSeamTool.delete_all_guides()          # シーンのガイドをすべて消す (確認する。Ctrl+Z で戻る)
    UVSeamTool.settings().setValue("guideColor", (1, 0, 0))   # 設定 (constants.SETTINGS_PATH の JSON に保存)
"""

import os

import maya.cmds as cmds

from .compat import accel
from .constants import CONTEXT_COMMAND, CONTEXT_NAME, PLUGIN_COMMANDS, PLUGIN_NAME
from .core.guide import editing
from .core.path.mesh_graph import MeshGraph
from .core.settings import settings as _settings
from .core.seam.seam import seam_edges
from .tool import guide_cleanup, tool_settings_window, uv_apply
from .tool.target_mesh import TargetMesh
from .utils import log, uv_editor
from .utils.mesh import Mesh
from .utils.selection import selected_meshes

__all__ = ["cut_guides", "cut_path", "delete_all_guides", "delete_guides", "list_guides", "load_plugin",
           "settings", "sew_guides", "show_tool_settings", "tool"]


def tool():
    """プラグインを読み込んで、このツールにする。"""
    load_plugin()
    if not cmds.contextInfo(CONTEXT_NAME, exists=True):
        getattr(cmds, CONTEXT_COMMAND)(CONTEXT_NAME)

    cmds.setToolTo(CONTEXT_NAME)


def show_tool_settings():
    """ツール設定のウィンドウを開く (ツールになっていなければ先にツールにする)。"""
    if cmds.currentCtx() != CONTEXT_NAME:
        tool()

    tool_settings_window.open_window()


def load_plugin():
    """プラグインが読み込まれていなければ読み込む。登録が足りなければ (コマンドを足したあと) 読み直す。

    起動用のバッチが plug-ins/ を MAYA_PLUG_IN_PATH に足していれば名前で読める。足していなければフルパスで読む。
    """
    if cmds.pluginInfo(PLUGIN_NAME, query=True, loaded=True):
        if all(hasattr(cmds, name) for name in PLUGIN_COMMANDS):
            return

        # プラグインのコマンドが Undo の列に残っていると外せないので、Undo の履歴を消してから外す
        log.warning("プラグインのコマンドが足りないので読み直します (Undo の履歴は消えます)")
        cmds.flushUndo()
        cmds.unloadPlugin(PLUGIN_NAME)

    try:
        cmds.loadPlugin(PLUGIN_NAME + ".py", quiet=True)
    except RuntimeError:
        cmds.loadPlugin(_plugin_path(), quiet=True)


def cut_guides(mesh_name=None):
    """メッシュの確定したガイドすべてのエッジで UV をカットする。カットしたエッジの数を返す。"""
    return _apply_guides(mesh_name, uv_apply.CUT)


def sew_guides(mesh_name=None):
    """メッシュの確定したガイドすべてのエッジで UV を縫合する。縫合したエッジの数を返す。"""
    return _apply_guides(mesh_name, uv_apply.SEW)


def settings():
    """設定 (core.settings.settings.Settings)。

        UVSeamTool.settings().setValue("guideColor", (1, 0, 0))   # 変えるとすぐ保存して、ビューも描き直す
        UVSeamTool.settings().reset()                              # すべて既定に戻す
    """
    return _settings.current()


def list_guides():
    """ガイドを保存しているメッシュごとの [{"mesh", "guides", "usable"}] (ログにも出す)。"""
    return guide_cleanup.list_guides()


def delete_guides(mesh_names=None):
    """メッシュ (トランスフォームの名前のリスト。省くと選んでいるメッシュ) に保存したガイドを消す。1 回の Undo。"""
    load_plugin()   # Undo のコマンドを使うため
    if mesh_names is None:
        meshes = selected_meshes()
    else:
        meshes = [Mesh.fromName(name) for name in mesh_names]

    return guide_cleanup.delete_guides(meshes)


def delete_all_guides(confirm=True):
    """シーンに保存したガイドをすべて消す。confirm なら (GUI のとき) 確認する。1 回の Undo。"""
    load_plugin()

    return guide_cleanup.delete_all_guides(confirm)


def cut_path(vertices, mesh_name=None):
    """頂点の列を順に最短パスでつないだガイドを作り、そのエッジで UV をカットする。

    mesh_name はメッシュのトランスフォームの名前。省くと、選んでいる最初のメッシュ。
    戻り値は (ガイド, カットしたエッジの番号の tuple)。つながらない点があれば (None, ())。
    """
    accel.require()
    mesh = _mesh_of(mesh_name)

    # 1. Maya から読む (utils) -> 2. グラフを作る (core)
    graph = MeshGraph(mesh.points(), mesh.edgeVertices(), _settings.current().value("straightness"))

    # 3. ガイドを作る: 最初の点 -> 点を 1 つずつ足す (足すたびに区間を最短パスで求める)
    guide = editing.new_guide(0, vertices[0])
    for vertex in vertices[1:]:
        guide = editing.add_point(guide, graph, vertex)
        if guide is None:
            log.warning("頂点 {} にはつながっていません".format(vertex))
            return None, ()

    # 4. ガイド -> エッジ (core) -> 5. UV をカット (utils)
    seam = seam_edges(guide, graph)
    uv_editor.cut_edges(mesh, seam)
    log.info("{}: {} 本のエッジでカットしました".format(mesh.name(), len(seam)))

    return guide, seam


def _apply_guides(mesh_name, operation):
    # シェイプに保存したガイドを読んで (TargetMesh)、確定したガイドすべてに当てる
    accel.require()
    target    = TargetMesh(_mesh_of(mesh_name))
    guide_set = target.guideSet()
    guides    = [guide for guide in guide_set.guides if guide.id != guide_set.active_id]

    return uv_apply.apply_guides(target.mesh(), target.graph(), guides, operation)


def _mesh_of(mesh_name):
    if mesh_name is not None:
        return Mesh.fromName(mesh_name)

    meshes = selected_meshes()
    if not meshes:
        raise ValueError("メッシュを選ぶか、mesh_name を渡してください")

    return meshes[0]


def _plugin_path():
    # scripts/UVSeamTool から見た ../../plug-ins/uvSeamTool.py
    here = os.path.dirname(os.path.abspath(__file__))

    return os.path.normpath(os.path.join(here, "..", "..", "plug-ins", PLUGIN_NAME + ".py"))
