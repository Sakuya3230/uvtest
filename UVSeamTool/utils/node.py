"""
Maya のノードの名前と API の型 (MObject / MDagPath) の変換。

名前は、同じ名前のノードがあっても 1 つに決まるフルパスで扱うのを基本にする。
"""

import maya.api.OpenMaya as om


def mobject_from_name(name):
    """名前 -> MObject。見つからなければ ValueError。"""
    return _selection_of(name).getDependNode(0)


def dag_path_from_name(name):
    """名前 -> MDagPath。見つからない・DAG のノードでなければ ValueError。"""
    try:
        return _selection_of(name).getDagPath(0)
    except TypeError:
        raise ValueError("DAG のノードではありません: {}".format(name))


def full_path(dag_path):
    """MDagPath -> フルパス ("|group1|pSphere1")。"""
    return dag_path.fullPathName()


def short_name(dag_path):
    """MDagPath -> 名前だけ ("pSphere1")。"""
    return om.MFnDagNode(dag_path).name()


def mesh_shape_path(transform_path):
    """トランスフォームの下のメッシュのシェイプの MDagPath。無ければ None。

    中間オブジェクト (デフォーマの元の形) は飛ばす。
    """
    for index in range(transform_path.childCount()):
        child = om.MDagPath(transform_path)
        child.push(transform_path.child(index))
        if child.apiType() == om.MFn.kMesh and not om.MFnDagNode(child).isIntermediateObject:
            return child

    return None


def mesh_transform_path(dag_path):
    """メッシュのシェイプかトランスフォームの MDagPath -> メッシュを持つトランスフォームの MDagPath。

    メッシュでなければ None。
    """
    path = om.MDagPath(dag_path)
    if path.apiType() == om.MFn.kMesh:
        path.pop()   # シェイプならトランスフォームに上がる

    if path.apiType() != om.MFn.kTransform or mesh_shape_path(path) is None:
        return None

    return path


def _selection_of(name):
    selection = om.MSelectionList()
    try:
        selection.add(name)
    except RuntimeError:
        raise ValueError("ノードが見つかりません: {}".format(name))

    return selection
