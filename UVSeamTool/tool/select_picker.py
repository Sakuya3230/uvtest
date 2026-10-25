"""
選択のサブツールが、画面の上でマウスの下のエッジを拾う。
"""

from ..compat.accel import np
from ..utils import picking


class SelectPicker:
    """マウスの下のエッジを拾う (表の面に当たった点に、いちばん近いその面のエッジ)。

    エッジは (TargetMesh, エッジの番号) で返す。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, targets):
        self._targets = targets

    # -- 公開メソッド ---------------------------------------------------------
    def edgeAt(self, x, y):
        """(x, y) の下の (TargetMesh, エッジの番号)。無ければ None。"""
        targets            = list(self._targets)
        index, face, point = picking.pick_face([target.mesh() for target in targets], x, y)
        if index is None:
            return None

        target   = targets[index]
        topology = target.edgeTopology()
        world    = target.worldPoints()
        hit      = np.array(point)
        edge     = min(topology.faceEdges(face),
                       key=lambda e: _distance_to_segment(hit, *(world[v] for v in topology.edgeVertices(e))))

        return target, edge


def _distance_to_segment(point, a, b):
    # 3D の点から線分 a-b までの距離
    direction = b - a
    length    = float(np.dot(direction, direction))
    t         = 0.0 if length == 0.0 else min(1.0, max(0.0, float(np.dot(point - a, direction)) / length))

    return float(np.linalg.norm(point - (a + t * direction)))
