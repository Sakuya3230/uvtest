"""
編集のサブツールが、画面の上でガイド・点・点を挿入する場所を拾う。
"""

from ..core.guide import guide_picking
from ..core.guide.guide_point import vertex_point
from ..utils import view

_PICK_DISTANCE  = 8.0    # ガイドの線からこのピクセル以内なら拾う
_POINT_DISTANCE = 10.0   # 点からこのピクセル以内なら拾う (線より優先)


class EditPicker:
    """ガイドの線・点を画面に写し、マウスの位置・矩形から拾う (計算は core.guide.guide_picking)。

    ガイドは ref (メッシュの鍵, ガイドの id) で返す。点・挿入する場所は、選んでいるガイド (selected の ref) のものだけ。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, targets):
        self._targets = targets

    # -- 公開メソッド ---------------------------------------------------------
    def guideAt(self, x, y):
        """(x, y) にいちばん近いガイドの ref (無ければ None)。"""
        return guide_picking.nearest_guide(self._screen_lines(), (x, y), _PICK_DISTANCE)

    def guidesInRect(self, rect):
        """矩形 (左, 下, 右, 上) に線がかかるガイドの ref のリスト。"""
        return guide_picking.guides_in_rect(self._screen_lines(), rect)

    def pointAt(self, x, y, selected):
        """(x, y) にいちばん近い、選んでいるガイドの点 (ref, 点の番号)。無ければ None。"""
        return guide_picking.nearest_point(self._screen_points(selected), (x, y), _POINT_DISTANCE)

    def pointsInRect(self, rect, selected):
        """矩形 (左, 下, 右, 上) の中の、選んでいるガイドの点 (ref, 点の番号) のリスト。"""
        return guide_picking.points_in_rect(self._screen_points(selected), rect)

    def insertAt(self, x, y, selected):
        """(x, y) に点を挿入するなら (ref, 区間の番号, 点 (GuidePoint))。無ければ None。

        選んでいるガイドのシームの上の、いちばん近い頂点の頂点の点。
        """
        screen_segments = []
        for target, guide in self._guides(selected):
            for index, segment in enumerate(guide.segments):
                pixels = view.world_to_view(target.positions(segment.seam))
                screen_segments.append(((target.key(), guide.id), index, segment.seam, pixels))

        found = guide_picking.nearest_line_vertex(screen_segments, (x, y), _PICK_DISTANCE)
        if found is None:
            return None

        ref, index, vertex = found

        return ref, index, vertex_point(vertex)

    # -- 非公開メソッド -------------------------------------------------------
    def _guides(self, selected):
        # selected (ref の集合) のガイドの [(TargetMesh, Guide)]
        return [(target, guide) for target in self._targets for guide in target.guideSet().guides
                if (target.key(), guide.id) in selected]

    def _screen_points(self, selected):
        # 選んでいるガイドの点を画面に写した [(ref, 点の番号, (x, y))]
        screen_points = []
        for target, guide in self._guides(selected):
            pixels = view.world_to_view(target.pointPositions(guide.points))
            screen_points.extend(((target.key(), guide.id), index, pixel) for index, pixel in enumerate(pixels))

        return screen_points

    def _screen_lines(self):
        # すべてのガイドの線 (区間のシーム。区間の無いガイドは点の位置) を画面に写した [(ref, [(x, y)])]
        return [((target.key(), guide.id), view.world_to_view(target.guidePositions(guide)))
                for target in self._targets for guide in target.guideSet().guides]
