"""
Maya の対称 (symmetricModelling) の設定を読む。
"""

import maya.cmds as cmds


def maya_symmetry():
    """Maya の対称がオンで、空間がワールドかオブジェクトなら (空間, 軸, 許容値)。それ以外 (オフ・トポロジー) なら None。

    空間は "world" / "object"、軸は "x" / "y" / "z" (設定の mirrorSpace / mirrorAxis と同じ値)。
    """
    if not cmds.symmetricModelling(query=True, symmetry=True):
        return None

    space = cmds.symmetricModelling(query=True, about=True)
    if space not in ("world", "object"):
        return None   # トポロジーの対称は、ツールの設定を使う

    axis      = cmds.symmetricModelling(query=True, axis=True)
    tolerance = cmds.symmetricModelling(query=True, tolerance=True)

    return space, axis, float(tolerance)
