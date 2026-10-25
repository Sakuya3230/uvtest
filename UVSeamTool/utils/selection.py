"""
Maya の選択からメッシュ・エッジを取る / エッジを選ぶ・メッシュをエッジの選択モードにする。
"""

import maya.api.OpenMaya as om
import maya.cmds as cmds

from . import node
from .mesh import Mesh

_OTHER_COMPONENTS = ("vertex", "facet", "polymeshUV", "polymeshVtxFace")   # エッジの選択モードでは選べない種類 (is_edge_mode)


def selected_meshes():
    """選んでいるメッシュ (Mesh) のリスト。選んだ順・重なりなし。

    トランスフォーム・シェイプ・コンポーネント (頂点など) のどれを選んでいても、そのメッシュになる。
    """
    selection = om.MGlobal.getActiveSelectionList()
    meshes    = []
    seen      = set()

    for index in range(selection.length()):
        try:
            path = selection.getDagPath(index)
        except TypeError:
            continue   # DAG のノードではない (マテリアルなど)

        transform_path = node.mesh_transform_path(path)
        if transform_path is None:
            continue

        key = transform_path.fullPathName()
        if key not in seen:
            seen.add(key)
            meshes.append(Mesh(transform_path))

    return meshes


def selected_edges():
    """選んでいるエッジの [(Mesh, エッジの番号のリスト)]。エッジ以外の選択は見ない。"""
    selection = om.MGlobal.getActiveSelectionList()
    found     = {}
    for index in range(selection.length()):
        try:
            path, component = selection.getComponent(index)
        except TypeError:
            continue   # DAG のノードではない

        if component.isNull() or component.apiType() != om.MFn.kMeshEdgeComponent:
            continue

        transform_path = node.mesh_transform_path(path)
        if transform_path is None:
            continue

        mesh  = Mesh(transform_path)
        edges = om.MFnSingleIndexedComponent(component).getElements()
        found.setdefault(mesh.key(), (mesh, []))[1].extend(edges)

    return [(mesh, sorted(set(edges))) for mesh, edges in found.values()]


REPLACE = "replace"
TOGGLE  = "toggle"
ADD     = "add"
REMOVE  = "deselect"


def click_mode(shift, ctrl):
    """クリック・矩形の修飾キー -> 選び方 (Maya と同じ: なし = 置き換え / Shift = 切り替え / Ctrl = 外す / Ctrl+Shift = 足す)。"""
    if shift and ctrl:
        return ADD

    if ctrl:
        return REMOVE

    return TOGGLE if shift else REPLACE


def double_click_mode(shift, ctrl):
    """ダブルクリックの修飾キー -> 選び方。Shift は足す (1 回目のクリックで切り替えたエッジを、また切り替えて戻さないため)。"""
    if ctrl and not shift:
        return REMOVE

    return ADD if shift else REPLACE


def select_edges(items, mode):
    """[(Mesh, エッジの番号のリスト)] を Maya の選択にする (mode は REPLACE / TOGGLE / ADD / REMOVE)。

    メッシュにまたがっても 1 回の cmds.select (Maya と同じく、1 回の Undo に載る)。
    """
    names = [name for mesh, edges in items for name in mesh.edgeNames(edges)]
    if names:
        cmds.select(names, **{mode: True})


def clear_selection():
    """選択を外す (何も無い所をクリック。Undo に載る)。"""
    cmds.select(clear=True)


def edges_in_rect(rect):
    """画面の矩形 (左, 下, 右, 上。ビューのピクセル) に、Maya の矩形選択と同じ決まりで入るエッジ [(Mesh, エッジ)]。

    隠れたものは入らない (Maya と同じ)。MGlobal.selectFromScreen で選んで読み、選択はすぐ元に戻す (Undo には積まれない)。
    選び方 (置き換え・切り替えなど) は、呼ぶ側が反対側なども足してから select_edges で決める。
    """
    before = om.MGlobal.getActiveSelectionList()
    left, bottom, right, top = (int(round(value)) for value in rect)
    try:
        om.MGlobal.selectFromScreen(left, bottom, right, top, om.MGlobal.kReplaceList)
        inside = selected_edges()
    finally:
        om.MGlobal.setActiveSelectionList(before)

    return inside


def enter_edge_mode(meshes):
    """メッシュ (Mesh のリスト) をエッジの選択モードにする (右クリックのマーキングメニューの「エッジ」と同じ)。

    Undo には積まない。積むと、Ctrl+Z の 1 回目がハイライトを戻すだけになり、ガイドの編集などの Undo が 1 回ずれる。
    MEL の doMenuComponentSelection は、マーキングメニューを一度も使っていないと読み込まれていないので
    (旧版で確認)、同じことを cmds で行う:
      オブジェクトの選択モード     ハイライトしたオブジェクト用のマスク (objectComponent) をエッジだけにしてハイライト
      コンポーネントの選択モード   マスクをエッジだけにしてハイライト
    """
    names = [mesh.fullPath() for mesh in meshes if mesh.isValid()]
    if not names:
        return

    state = cmds.undoInfo(query=True, stateWithoutFlush=True)
    cmds.undoInfo(stateWithoutFlush=False)
    try:
        if cmds.selectMode(query=True, object=True):
            cmds.selectType(objectComponent=True, allComponents=False)
            cmds.selectType(objectComponent=True, edge=True)
            cmds.selectType(edge=True)
        else:
            cmds.selectType(allComponents=False)
            cmds.selectType(edge=True)
        cmds.hilite(names)
    finally:
        cmds.undoInfo(stateWithoutFlush=state)


def is_edge_mode(meshes):
    """エッジの選択モード (enter_edge_mode のあとの状態) か。エッジのほかのコンポーネント (頂点・面・UV など) も
    選べる状態なら False。オブジェクトの選択モードなら、メッシュがすべてハイライトされていること。
    """
    if cmds.selectMode(query=True, component=True):
        flags = {}
    else:
        hilited = set(cmds.ls(hilite=True, long=True) or [])
        if any(mesh.fullPath() not in hilited for mesh in meshes if mesh.isValid()):
            return False
        flags = {"objectComponent": True}

    if not cmds.selectType(query=True, edge=True, **flags):
        return False

    return not any(cmds.selectType(query=True, **dict(flags, **{name: True})) for name in _OTHER_COMPONENTS)
