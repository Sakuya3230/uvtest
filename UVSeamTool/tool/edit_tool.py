"""
ガイドを編集するサブツール (5a: ガイドを選ぶ・消す / 5b: 点を動かす / 5c: 点の挿入・選択・削除)。
"""

import maya.api.OpenMayaUI as omui

from ..core.guide import editing, guide_picking, set_editing
from ..utils import log
from . import edit_operations, guide_edit
from .edit_picker import EditPicker
from .guide_drawing import color, draw_guides
from .point_dragging import PointDragging
from .sub_tool import SubTool

_MARQUEE_START  = 4.0    # 何も無い所からこのピクセル以上動かしたら矩形選択 (それより短ければクリック)
_MARQUEE_COLOR  = (1.0, 1.0, 1.0)


class EditTool(SubTool):
    """ガイドを選んで編集する。

    ガイド: クリック = 選ぶ (Shift = 切り替え / Ctrl = 外す / Ctrl+Shift = 足す)
            何も無い所からドラッグ = 矩形にかかったガイドを選ぶ (修飾キーは同じ)
            ガイドを選んでいるときの矩形 = そのガイドの点を選ぶ (メッシュを選んでから頂点を矩形で選ぶのと同じ考え方)
            何も無い所をクリック = 点の選択を外す (点を選んでいなければ、ガイドの選択を外す)
            左ボタンはすべてこのサブツールが受け取る (Maya の選択は使わない。カメラの Alt + マウスは Maya のまま)
    点 (選んでいるガイドのもの): ドラッグ = つかんだ点を選んでいる点に足し、選んでいる点をまとめて動かす /
            クリック = 選ぶ (Shift / Ctrl で切り替え / 外す)。ドラッグの中身は tool.point_dragging
    選んでいるガイドの線: クリック = そこに点を挿入 (そのままドラッグで動かす。挿入と移動で 1 回の Undo)
    Delete = 選んでいる点を消す (点を選んでいなければ、選んでいるガイドを消す) / Esc = 点の選択 -> ガイドの選択を外す
    カット / 縫合・区間の作り方の切り替えの対象は、選んでいるガイド (と点。中身は tool.edit_operations)。
    選択は Undo に積まない (ガイドの形の変更だけを戻す)。

    複数のメッシュ (tool.targets.Targets): ガイドは (メッシュの鍵, ガイドの id) の組 (ref) で指す。
    削除・カット / 縫合は、メッシュにまたがっても 1 回の Undo。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, targets):
        self._targets           = targets
        self._picker            = EditPicker(targets)   # 画面の上でガイド・点・挿入する場所を拾う
        self._dragging          = PointDragging()   # 点のドラッグ (1 点・まとめて)
        self._selected          = frozenset()   # 選んでいるガイドの ref (メッシュの鍵, ガイドの id)
        self._selected_points   = frozenset()   # 選んでいる点 (ref, 点の番号)
        self._hovered           = None          # マウスの下のガイドの ref
        self._hovered_point     = None          # マウスの下の点 (ref, 点の番号)。選んでいるガイドの点だけ
        self._hovered_insert    = None          # マウスの下の、点を挿入できる所 (メッシュの鍵, GuidePoint)
        self._marquee_start     = None          # 何も無い所で押した (x, y, shift, ctrl)。矩形選択か、選択を外すクリック
        self._marquee_rect      = None          # ドラッグ中の矩形 (左, 下, 右, 上)。まだ短ければ None

    # -- 上書きするメソッド (SubTool) -----------------------------------------
    def deactivate(self):
        self._clear_hover()
        self.cancel()

    def refresh(self):
        # ガイドの組が変わった (Undo も)。消えたガイドは選択から外し、点の選択は外す (番号がずれるため)
        existing              = {(target.key(), guide.id) for target in self._targets for guide in target.guideSet().guides}
        self._selected        = self._selected & existing
        self._selected_points = frozenset()
        self._clear_hover()

    def hover(self, x, y):
        point  = self._picker.pointAt(x, y, self._selected)
        insert = None if point is not None else self._picker.insertAt(x, y, self._selected)
        guide  = None if point is not None or insert is not None else self._picker.guideAt(x, y)
        state  = (point, (insert[0][0], insert[2]) if insert is not None else None, guide)
        if state == (self._hovered_point, self._hovered_insert, self._hovered):
            return False

        self._hovered_point, self._hovered_insert, self._hovered = state

        return True

    def draw(self, painter):
        dragging = self._dragging
        preview  = dragging.preview()
        for target in self._targets:
            key = target.key()
            draw_guides(painter, target,
                        selected={guide_id for k, guide_id in self._selected if k == key},
                        hovered=self._hovered[1] if self._hovered is not None and self._hovered[0] == key else None,
                        replaced=preview if dragging.target() is target else None)

        for ref, index in self._selected_points:
            target, guide = self._find(ref)
            if preview is not None and dragging.target() is target:
                guide = set_editing.find_guide(preview, guide.id) or guide   # 動かしている最中は、プレビューの位置に描く
            painter.dots(target.pointPositions([guide.points[index]]), color("selectedPointColor"), size=color("pointSize") + 3.0)

        if self._marquee_rect is not None:
            painter.rect2d(self._marquee_rect, _MARQUEE_COLOR)

        if dragging.isActive() or self._marquee_start is not None:
            return

        if self._hovered_point is not None:
            ref, index    = self._hovered_point
            target, guide = self._find(ref)
            painter.dots(target.pointPositions([guide.points[index]]), color("hoverPointColor"), size=color("pointSize") + 4.0)
        elif self._hovered_insert is not None:
            key, point = self._hovered_insert
            painter.dots(self._targets.find(key).pointPositions([point]), color("insertColor"), size=color("pointSize") - 1.0)

    def press(self, x, y, button, shift, ctrl):
        if button != omui.MEvent.kLeftMouse:
            return False

        point = self._picker.pointAt(x, y, self._selected)
        if point is not None:
            if shift or ctrl:
                self._selected_points = guide_picking.combine_selection(self._selected_points, point, shift, ctrl)
            else:
                # つかんだ点は選んでいる点に足し、同じメッシュの選んでいる点をまとめて動かす
                # (動かさずに離したら、クリックとしてその点だけを選ぶ。release)
                target, guide         = self._find(point[0])
                self._selected_points = self._selected_points | {point}
                group                 = {(ref[1], index) for ref, index in self._selected_points if ref[0] == point[0][0]}
                self._dragging.start(target, guide, point[1], group=group)
            return True

        insert = None if (shift or ctrl) else self._picker.insertAt(x, y, self._selected)
        if insert is not None:
            # シームの上のいちばん近い頂点に足す (区間をその頂点で分ける)
            ref, segment_index, new_point = insert
            target, guide                 = self._find(ref)
            inserted                      = editing.insert_point(guide, segment_index, new_point.vertex)
            if inserted is not None:
                self._dragging.start(target, inserted, segment_index + 1, inserted=True)
                return True

        ref = self._picker.guideAt(x, y)
        if ref is None:
            # 何も無い所: 離すまでに動かせば矩形選択、動かさなければ選択を外す (Maya の選択には渡さない)
            self._marquee_start = (x, y, shift, ctrl)
            self._marquee_rect  = None
            return True

        self._selected_points = frozenset()   # ガイドを選び直すときは、点の選択を外す
        self._selected        = guide_picking.combine_selection(self._selected, ref, shift, ctrl)
        log.debug("選んでいるガイド: {}".format(len(self._selected)))

        return True

    def doubleClick(self, x, y, shift, ctrl):
        # 受け取って何もしない (ダブルクリックを Maya に渡さない)
        return True

    def drag(self, x, y):
        if self._marquee_start is not None:
            return self._drag_marquee(x, y)

        return self._dragging.moveTo(x, y) if self._dragging.isActive() else False

    def release(self, x, y):
        if self._marquee_start is not None:
            self._release_marquee()
            return True

        if not self._dragging.isActive():
            return False

        grabbed                          = self._dragging.grabbed()
        target, new_set, inserted, moved = self._dragging.finish()
        if not moved:
            # 動かさずに離した: その点だけを選ぶ
            self._selected_points = frozenset([((target.key(), grabbed[0]), grabbed[1])])
            return True

        if new_set is not None:
            kept = self._selected_points
            guide_edit.apply(target, new_set)   # ガイドの組が変わるので refresh() が点の選択を外す
            if not inserted:
                self._selected_points = kept    # 動かしただけなら点の番号は変わらないので、選択を戻す
            log.debug("点を{}しました".format("挿入" if inserted else "動か"))

        return True

    def isBusy(self):
        return self._dragging.isActive() or self._marquee_start is not None

    def cancel(self):
        # ドラッグ・矩形選択をやめる (組・選択は変えていない)。このあと届く離しは、release が何もしない
        self._dragging.cancel()
        self._marquee_start = None
        self._marquee_rect  = None

    def applyOperation(self, operation):
        edit_operations.apply_to_selection(self._targets, self._selected, operation)

    def splitPoints(self):
        edit_operations.split_selection(self._targets, self._selected_points)

    def joinGuides(self):
        edit_operations.join_selection(self._targets, self._selected, self._selected_points)

    def abort(self):
        if self._selected_points:
            self._selected_points = frozenset()
        else:
            self._selected = frozenset()

    def delete(self):
        # 消したガイド・点は refresh() で選択から外れる
        edit_operations.delete_selection(self._targets, self._selected, self._selected_points)

    # -- 非公開メソッド -------------------------------------------------------
    def _find(self, ref):
        # ref (メッシュの鍵, ガイドの id) -> (TargetMesh, Guide)
        target = self._targets.find(ref[0])

        return target, set_editing.find_guide(target.guideSet(), ref[1])

    def _drag_marquee(self, x, y):
        start_x, start_y, _, _ = self._marquee_start
        if self._marquee_rect is None and max(abs(x - start_x), abs(y - start_y)) < _MARQUEE_START:
            return False   # まだクリックのうち

        self._marquee_rect = (min(start_x, x), min(start_y, y), max(start_x, x), max(start_y, y))

        return True

    def _release_marquee(self):
        _, _, shift, ctrl = self._marquee_start
        rect              = self._marquee_rect
        self.cancel()

        if rect is None:
            if not (shift or ctrl):
                self.abort()   # 何も無い所をクリック: 点の選択 -> ガイドの選択の順に外す (Esc と同じ)
            return

        if self._selected:
            # ガイドを選んでいる: そのガイドの点を選ぶ
            points                = self._picker.pointsInRect(rect, self._selected)
            self._selected_points = guide_picking.combine_selection_many(self._selected_points, points, shift, ctrl)
            log.debug("矩形で選んだ点: {} つ (選んでいる点: {} つ)".format(len(points), len(self._selected_points)))
            return

        refs           = self._picker.guidesInRect(rect)
        self._selected = guide_picking.combine_selection_many(self._selected, refs, shift, ctrl)
        log.debug("矩形で選んだガイド: {} 本 (選んでいるガイド: {} 本)".format(len(refs), len(self._selected)))

    def _clear_hover(self):
        self._hovered        = None
        self._hovered_point  = None
        self._hovered_insert = None
