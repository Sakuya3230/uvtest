"""
ツールの対象のメッシュの集まり。
"""

from ..utils import picking
from .target_mesh import TargetMesh


class Targets:
    """対象のメッシュ (TargetMesh) の集まり。作成と編集のサブツールが共有する。

    ツールにしたときに選んでいたメッシュすべて。ツールを使っている間に選んだメッシュは add で加える
    (選択を外しても対象からは外さない)。メッシュが消されたら remove で外す。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, meshes):
        self._targets = [TargetMesh(mesh) for mesh in meshes]

    def __len__(self):
        return len(self._targets)

    def __iter__(self):
        return iter(list(self._targets))

    # -- 公開メソッド ---------------------------------------------------------
    def find(self, key):
        """メッシュの鍵の TargetMesh (無ければ None)。"""
        for target in self._targets:
            if target.key() == key:
                return target

        return None

    def add(self, mesh):
        """メッシュを対象に加え、その TargetMesh を返す。もう対象なら何もせず None。"""
        if self.find(mesh.key()) is not None:
            return None

        target = TargetMesh(mesh)
        self._targets.append(target)

        return target

    def remove(self, key):
        self._targets = [target for target in self._targets if target.key() != key]

    def pick(self, x, y):
        """ピクセル (x, y) の下の (TargetMesh, 頂点の番号)。いちばん手前のメッシュ。当たらなければ (None, None)。"""
        index, vertex = picking.pick_vertex([target.mesh() for target in self._targets], x, y)
        if index is None:
            return None, None

        return self._targets[index], vertex

