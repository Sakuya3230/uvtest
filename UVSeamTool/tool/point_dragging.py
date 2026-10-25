"""
編集のモードの点のドラッグ (1 点・選んだ点をまとめて)。EditTool が押す・動かす・離すを渡す。
"""

from ..core.guide import set_editing
from ..core.guide.group_drag import GroupDrag
from ..core.guide.guide_point import vertex_point
from ..core.guide.point_drag import PointDrag
from ..utils import picking


class PointDragging:
    """点を 1 つ動かす (core.guide.point_drag.PointDrag) か、選んだ点をまとめて動かす (core.guide.group_drag.GroupDrag)。

    つかんだ点はマウスの下の頂点に吸い付く。まとめて動かすときは、ほかの点はつかんだ点の移動量だけ動く。
    動かす前から見せるのは挿入した点だけ (挿入と移動で 1 回の Undo)。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self):
        self._drag      = None          # PointDrag か GroupDrag
        self._target    = None          # 動かしている点のメッシュ (TargetMesh)
        self._guide     = None          # つかんだ点のガイド (動かす前)
        self._index     = None          # つかんだ点の番号
        self._preview   = None          # 動かしている間の組 (まだ Maya には書いていない)
        self._inserted  = False         # 点を挿入してからのドラッグか (動かさなくても挿入は確定する)

    # -- 公開メソッド ---------------------------------------------------------
    def start(self, target, guide, index, inserted=False, group=()):
        """target の guide (組の中のものか、挿入したガイド) の index 番目の点をつかむ。

        group は一緒に動かす点 ({(ガイドの id, 点の番号)}。つかんだ点を含む)。2 つ以上ならまとめて動かす。
        """
        self._target    = target
        self._guide     = guide
        self._index     = index
        self._inserted  = inserted
        if len(group) >= 2 and not inserted:
            self._drag    = GroupDrag(target.guideSet(), target, group, (guide.id, index))
            self._preview = None
        else:
            self._drag    = PointDrag(guide, target, index)
            self._preview = _with_guide(target.guideSet(), guide) if inserted else None   # 挿入した点は動かす前から見せる

    def isActive(self):
        return self._drag is not None

    def target(self):
        return self._target

    def preview(self):
        """動かしている間の組 (動かしていなければ None)。描く所が、このメッシュのガイドの代わりに描く。"""
        return self._preview

    def moveTo(self, x, y):
        """マウスを (x, y) へ動かした。プレビューが変わったら True。"""
        vertex = picking.vertex_under_cursor(self._target.mesh(), x, y)
        if vertex is None:
            return False   # メッシュの外では、最後の位置のまま

        point = vertex_point(vertex)
        if self._preview is None and point == self._guide.points[self._index]:
            return False   # まだ同じ頂点の上 (手の揺れ)。離せばクリック (点を選ぶ) になる

        if isinstance(self._drag, GroupDrag):
            moved = self._drag.moved(point)
        else:
            guide = self._drag.moved(point)
            moved = _with_guide(self._target.guideSet(), guide) if guide is not None else None
        if moved is None or moved == self._preview:
            return False

        self._preview = moved

        return True

    def finish(self):
        """離した。(メッシュ, 新しい組か None, 挿入だったか, 動かしたか)。新しい組が None なら変えない。"""
        target, preview, inserted = self._target, self._preview, self._inserted
        guide                     = self._guide
        self.cancel()
        if preview is None and not inserted:
            return target, None, inserted, False

        result = preview if preview is not None else _with_guide(target.guideSet(), guide)

        return target, (result if result != target.guideSet() else None), inserted, True

    def grabbed(self):
        """つかんだ点 (ガイドの id, 点の番号)。"""
        return self._guide.id, self._index

    def cancel(self):
        self._drag      = None
        self._target    = None
        self._guide     = None
        self._index     = None
        self._preview   = None
        self._inserted  = False


def _with_guide(guide_set, guide):
    # 同じ id のガイドを guide に替えた組 (無ければ足す。挿入したガイドは組の中の同じ id を替える)
    if set_editing.find_guide(guide_set, guide.id) is None:
        return set_editing.add_guide(guide_set, guide)

    return set_editing.replace_guide(guide_set, guide) or guide_set
