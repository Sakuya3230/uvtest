"""
メッシュのシェイプの文字列のアトリビュート (constants.GUIDE_ATTRIBUTE) を読み書きする。

API (MPlug) で読み書きする。cmds.setAttr だと Undo の列に別の 1 回として積まれるため
(書くのは utils.undo のコマンドの redo / undo の中なので、Undo はそのコマンドがまとめて扱う)。
"""

import maya.api.OpenMaya as om

from ..constants import GUIDE_ATTRIBUTE
from . import node
from .mesh import Mesh


def meshes_with_guides():
    """シーンの中で、アトリビュートを持つメッシュ (utils.mesh.Mesh) のリスト。シェイプごとに 1 つ。"""
    meshes   = []
    seen     = set()
    iterator = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kMesh)
    while not iterator.isDone():
        shape_path = iterator.getPath()
        iterator.next()

        shape_node = om.MFnDagNode(shape_path)
        if shape_node.isIntermediateObject or not shape_node.hasAttribute(GUIDE_ATTRIBUTE):
            continue

        shape_key = om.MObjectHandle(shape_path.node()).hashCode()
        if shape_key in seen:
            continue   # インスタンス (同じシェイプの別のパス)

        seen.add(shape_key)
        transform_path = node.mesh_transform_path(shape_path)
        if transform_path is not None:
            meshes.append(Mesh(transform_path))

    return meshes


def read_text(mesh):
    """シェイプのアトリビュートの文字列。アトリビュートが無ければ None。"""
    shape_node = _shape_node(mesh)
    if not shape_node.hasAttribute(GUIDE_ATTRIBUTE):
        return None

    return shape_node.findPlug(GUIDE_ATTRIBUTE, False).asString()


def write_text(mesh, text):
    """シェイプのアトリビュートに文字列を書く (無ければ作る)。ロックされたノードなどで書けなければ RuntimeError。"""
    shape_node = _shape_node(mesh)
    if not shape_node.hasAttribute(GUIDE_ATTRIBUTE):
        attribute = om.MFnTypedAttribute().create(GUIDE_ATTRIBUTE, GUIDE_ATTRIBUTE, om.MFnData.kString)
        shape_node.addAttribute(attribute)

    shape_node.findPlug(GUIDE_ATTRIBUTE, False).setString(text)


def delete(mesh):
    """シェイプのアトリビュートを消す。無ければ何もしない。消せなければ (リファレンスの元のファイルのものなど) RuntimeError。"""
    shape_node = _shape_node(mesh)
    if shape_node.hasAttribute(GUIDE_ATTRIBUTE):
        shape_node.removeAttribute(shape_node.attribute(GUIDE_ATTRIBUTE))


def _shape_node(mesh):
    return om.MFnDependencyNode(mesh.shapePath().node())
