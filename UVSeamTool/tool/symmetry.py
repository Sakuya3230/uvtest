"""
今の対称の面を決める (ツールの設定と、Maya の対称)。
"""

from dataclasses import dataclass

from ..core.settings import settings
from ..utils.symmetry import maya_symmetry


@dataclass(frozen=True)
class MirrorPlane:
    """対称の面 (変えられない値)。空間 ("object" / "world")・軸 ("x" / "y" / "z")・許容値と、Maya の対称から来たか。"""

    space       : str
    axis        : str
    tolerance   : float
    from_maya   : bool = False


def current_plane():
    """今の対称の面。対称が無ければ None。

    Maya の対称がオン (ワールド / オブジェクト) なら Maya の面 (ツールの「対称」がオフでも効く。旧版と同じ。
    Maya で対称を使っているときに、別に設定しなくてよいように)。そうでなければ、ツールの「対称」がオンのときだけ
    ツールの設定の面。
    """
    maya = maya_symmetry()
    if maya is not None:
        space, axis, tolerance = maya
        return MirrorPlane(space, axis, tolerance, from_maya=True)

    values = settings.current()
    if not values.value("symmetry"):
        return None

    return MirrorPlane(values.value("mirrorSpace"), values.value("mirrorAxis"), values.value("mirrorTolerance"))


def describe(plane):
    """ボタン・ログに出す短い文 ("対称 X" / "Maya 対称 Z" / "対称なし")。"""
    if plane is None:
        return "対称なし"

    return "{}対称 {}".format("Maya " if plane.from_maya else "", plane.axis.upper())
