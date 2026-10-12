# -*- coding: utf-8 -*-
"""
選択のモードの選択をシーンに行う (段階 16d)。

    select_edges([(shape, edges)], op)          # Maya の選択を変える (MEL の select なので Undo できる)
    front_edges(model, edges, camera)            # 表の面に付いているエッジだけ (矩形選択で裏側を選ばない)
    CameraInfo(eye, direction, ortho)            # 表 / 裏の判断に使うカメラ

仕組み:
- 選択は MEL の select で変える。Undo のキューに積まれる (1 回の操作 = 1 回の Undo)。Python の cmds.select
  だと Undo の記録の名前が空になる (ウェイトスライダーで確認) ので、MEL で呼ぶ (ダブルクリックで 1 回目の
  クリックを取り消すとき、直前の Undo がそれかを名前で確かめるため)。
  操作 (core.selection の REPLACE / TOGGLE / REMOVE / ADD) は select の -replace / -toggle / -deselect /
  -add。置き換えでエッジが無ければ選択を外す (メッシュの外をクリックしたとき)
- エッジの名前は範囲にまとめる (core.components.edge_component_names)
- スクリプトから選ぶと Maya の対称はかからない (mayapy で確認)。反対側はツールが足す
- 表の面: 面の法線がカメラの方を向いている (透視: 目の位置から面の中心へのベクトルと法線の内積が負。
  平行投影: 視線の向きと法線の内積が負)。ほかの部分に隠れているか (遮蔽) までは見ない
"""
import maya.api.OpenMaya as om
import maya.mel as mel

from ..core.components import edge_component_names
from ..core.selection import ADD, REMOVE, REPLACE, TOGGLE

__all__ = ["select_edges", "front_edges", "CameraInfo"]

_FLAGS = {REPLACE: "replace", TOGGLE: "toggle", REMOVE: "deselect", ADD: "add"}


def select_edges(pairs, op):
    """[(シェイプ, エッジ)] を op で選ぶ (Undo できる)。選んだ名前のリスト。

    置き換えでエッジが 1 本も無ければ、選択を外す。ほかの操作でエッジが無ければ何もしない。
    """
    names = []
    for shape, edges in pairs:
        if edges:
            names.extend(edge_component_names(shape, sorted(set(edges))))
    if not names:
        if op == REPLACE:
            mel.eval("select -clear;")
        return []
    mel.eval("select -{} {};".format(_FLAGS[op], " ".join('"{}"'.format(n) for n in names)))
    return names


class CameraInfo(object):
    """表 / 裏を決めるカメラ (ワールドの目の位置・視線の向き・平行投影か)。"""

    def __init__(self, eye, direction, ortho=False):
        self.eye = tuple(eye)
        self.direction = tuple(direction)
        self.ortho = ortho

    @staticmethod
    def fromView(view):
        camera = om.MFnCamera(view.getCamera())
        eye = camera.eyePoint(om.MSpace.kWorld)
        direction = camera.viewDirection(om.MSpace.kWorld)
        return CameraInfo((eye.x, eye.y, eye.z), (direction.x, direction.y, direction.z),
                          camera.isOrtho())


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def front_edges(model, edges, camera):
    """edges のうち、表の面 (カメラの方を向く面) に 1 つでも付いているエッジ。

    model は scene.mesh.MeshModel。面ごとの判断は 1 回だけ (覚えておく)。
    """
    fn = model.fn
    iterator = om.MItMeshEdge(model.path)
    facing = {}

    def front(face):
        value = facing.get(face)
        if value is None:
            normal = fn.getPolygonNormal(face, om.MSpace.kWorld)
            normal = (normal.x, normal.y, normal.z)
            if camera.ortho:
                value = _dot(normal, camera.direction) < 0.0
            else:
                corners = [model.point(v) for v in fn.getPolygonVertices(face)]
                center = tuple(sum(c[k] for c in corners) / len(corners) for k in range(3))
                to_face = tuple(center[k] - camera.eye[k] for k in range(3))
                value = _dot(normal, to_face) < 0.0
            facing[face] = value
        return value

    result = []
    for edge in edges:
        iterator.setIndex(edge)
        if any(front(face) for face in iterator.getConnectedFaces()):
            result.append(edge)
    return result
