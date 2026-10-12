# -*- coding: utf-8 -*-
"""
対称の面と、対応表の使い回し (段階 17)。

    plane = mirror_plane(settings.values())        # MirrorPlane(空間, 軸, 許容値, Maya の設定か)
    mirror, cached = cached_mirror_map(model, plane)   # 覚えておいた対応表か、作って覚える
    clear_cache()                                  # 覚えた対応表を捨てる (テスト)

仕組み:
- 対称の面: Maya の対称 (symmetricModelling) がオンでワールド / オブジェクトなら、Maya の面 (空間・軸・
  許容値) を使い、ツールの対称がオフでも両側に効かせる (maya_plane)。オフ (かトポロジー) なら、ツールの設定
  (mirrorSpace / mirrorAxis / mirrorTolerance)。
  経緯: いったんツールの設定だけにしたが、Maya の対称がオンだと選択のモードの選択そのものを Maya が両側に
  してしまい (API に選択の対称を切る方法が無い)、ツールの対称と二重にかかった (X と Z の両方)。
  ツールの中で面を 1 つにそろえるため、両方のモードで Maya を優先する (ユーザーの判断)。
  どちらを使っているかは、ツール設定のウィンドウ (空間・軸・許容値を灰色にし「Maya の対称: ...」) と
  ビューのボタンで見せる
- 対応表 (core.mirror.MirrorMap) は作るのに時間がかかる (scipy で数十 ms、Python で 0.4〜0.6 秒) ので使い回す:
    A  トポロジーが同じ間は作り直さない。反対側の組はつながりの性質なので、変形しても変わらない
       (作り直すと、ポーズを付けて左右がずれたメッシュで組が見つからなくなる)。鍵に位置は入れない
    B  (メッシュの UUID, 空間, 軸, 許容値, トポロジーの鍵) を鍵に、モジュールに覚えておく (CACHE_SIZE 個まで)。
       ツールを出入りしても使い回す。モジュールをリロード・Maya を閉じると消える
    C  (コンテキストが) ツールに入った直後、Maya が手すきのときに先に作る
- オブジェクトの空間なら、頂点のローカルの位置で対応を取る (Transform を動かしても組は同じ)
"""
from collections import OrderedDict

import maya.cmds as cmds

from ..core.mirror import AXES, DEFAULT_TOLERANCE, SPACES, MirrorMap

__all__ = ["MirrorPlane", "mirror_plane", "maya_plane", "plane_text", "maya_symmetry", "cached_mirror_map", "mirror_cache_key",
           "node_uuid", "clear_cache", "CACHE_SIZE"]

CACHE_SIZE = 8
_CACHE = OrderedDict()   # 鍵 -> MirrorMap (古い順)


class MirrorPlane(object):
    """対称の面。"""

    def __init__(self, space, axis, tolerance, from_maya):
        self.space = space            # "world" / "object"
        self.axis = axis              # "x" / "y" / "z"
        self.tolerance = tolerance
        self.from_maya = from_maya    # Maya の対称の設定から決めたか (ログ用)

    def key(self):
        return (self.space, self.axis, round(float(self.tolerance), 9))

    def __eq__(self, other):
        return isinstance(other, MirrorPlane) and self.key() == other.key()

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.key())

    def __repr__(self):
        return "MirrorPlane({} {} 許容値 {}{})".format(self.space, self.axis.upper(), self.tolerance,
                                                     " Maya の設定" if self.from_maya else "")


def maya_symmetry():
    """Maya の対称の設定 (オンか, about, axis, 許容値)。読めなければ (False, None, None, 既定)。"""
    try:
        tolerance = float(cmds.symmetricModelling(query=True, tolerance=True))
    except (RuntimeError, TypeError, ValueError):
        tolerance = DEFAULT_TOLERANCE
    try:
        on = bool(cmds.symmetricModelling(query=True, symmetry=True))
        about = cmds.symmetricModelling(query=True, about=True)
        axis = cmds.symmetricModelling(query=True, axis=True)
    except RuntimeError:
        return False, None, None, tolerance
    return on, about, axis, tolerance


def maya_plane(symmetry=None):
    """Maya の対称がオンでワールド / オブジェクトなら、その面 (MirrorPlane)。それ以外は None。

    symmetry は maya_symmetry() の結果 (テストで渡す)。省くと今の Maya の設定を読む。
    """
    on, about, axis, tolerance = symmetry if symmetry is not None else maya_symmetry()
    if on and about in SPACES and axis in AXES:
        return MirrorPlane(about, axis, tolerance, True)
    return None


def mirror_plane(values, symmetry=None):
    """対称の面 (MirrorPlane)。Maya の対称が効いていればそれ、無ければツールの設定の値から。"""
    plane = maya_plane(symmetry)
    if plane is not None:
        return plane
    return MirrorPlane(values["mirrorSpace"], values["mirrorAxis"], values["mirrorTolerance"], False)


def plane_text(plane):
    """面の表示 ("ワールド Z" など)。"""
    space = {"world": "ワールド", "object": "オブジェクト"}.get(plane.space, plane.space)
    return "{} {}".format(space, plane.axis.upper())


def node_uuid(name):
    """ノードの UUID (名前を変えても変わらない)。読めなければ名前。"""
    try:
        return (cmds.ls(name, uuid=True) or [name])[0]
    except RuntimeError:
        return name


def mirror_cache_key(model, plane):
    """対応表の鍵。位置は入れない (トポロジーが同じなら使い回す)。"""
    return (node_uuid(model.name()),) + plane.key() + (model.topologyKey(),)


def cached_mirror_map(model, plane, build=True):
    """(対応表, 覚えておいたものか)。無ければ作って覚える (build が False なら (None, False))。"""
    key = mirror_cache_key(model, plane)
    mirror = _CACHE.get(key)
    if mirror is not None:
        _CACHE.move_to_end(key)   # 最近使ったものを後ろに (古いものから捨てる)
        return mirror, True
    if not build:
        return None, False
    points = model.graph().points if plane.space == "world" else model.localPoints()
    mirror = MirrorMap(points, model.graph().edges, AXES.index(plane.axis), plane.tolerance)
    _CACHE[key] = mirror
    while len(_CACHE) > CACHE_SIZE:
        _CACHE.popitem(last=False)
    return mirror, False


def clear_cache():
    _CACHE.clear()
