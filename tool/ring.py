# -*- coding: utf-8 -*-
"""
輪切りのモード (段階 19)。コンテキスト (tool/context.py) に組み込む部品 (ミックスイン)。

    ringPress(pos)           押した: 対象のメッシュの頂点の画面の位置とトポロジーを用意する (ドラッグの間は同じ)
    ringDrag(pos, drawMgr)   動かした: 線を描き、線の両端の視線で切る面を作って、断面の境目をプレビュー
    ringRelease(pos)         離した: ドラッグならプレビューを残す (なめらかにする設定なら整える)。クリックなら確定
    confirmRing()            プレビューのループを区間として積む (ためる。自動カットなら実行も。1 回の Undo)
    clearRing()              プレビューを捨てる (Esc・モードを替えたとき)
    adjustRing(steps, tilt)  離したあとの微調整: ずらす (ホイール) / 傾ける (Shift+ホイール)。段階 21
    onWheel(delta, shift)    ビューのホイール (tool/keys.py のフィルターから)

Shift+ドラッグは縦の継ぎ目 (段階 21): 腕に沿って描くと、カメラから見て奥側の半分だけ。
    findRing(stroke)         切る面の境目 (メッシュ, scene.ring.RingFound) を、全メッシュから探す

流れ:
    押す -> ドラッグ (線とプレビューが追従) -> 離す (プレビューが残る) -> クリックで確定
                                                                       -> もう一度ドラッグで描き直し
                                                                       -> Esc で捨てる
コンテキストの属性 (targets・settings・_manip) と、ほかの部品のメソッド (mirrorFor・_run_edit・_other_edges・
syncMesh) を使う。断面の計算は core/section.py と scene/ring.py。
"""
import traceback

import maya.api.OpenMayaUI as omui
import maya.cmds as cmds

from .. import log
from ..core.actions import MODE_RING
from ..core import draw_list
from ..core.ring import MIN_LENGTH, Stroke
from ..core.section import plane_from_rays, shift_plane, tilt_plane, TILT_DEGREES
from ..core.session import OPERATION_LABELS
from ..scene import edit as scene_edit
from ..scene import mesh as scene_mesh
from ..scene.ring import RingTarget
from .drawing import draw_stroke, project_points, view_ray

__all__ = ["RingMixin", "RING_DRAG_THRESHOLD", "diagnose"]

RING_DRAG_THRESHOLD = 4   # この距離 (ピクセル) 以上動かしたらドラッグ (それ未満はクリック)


def _ray_tuple(ray):
    """view_ray の (MPoint, MVector) をタプルに。"""
    source, direction = ray
    return (source.x, source.y, source.z), (direction.x, direction.y, direction.z)


class RingMixin(object):
    """輪切りのモード (UVPathCutContext に組み込む)。"""

    # -- マウス -------------------------------------------------------------------

    def _report_ring_error(self, where):
        """押す・ドラッグの中のエラーを、1 回の操作につき 1 回だけスクリプトエディタに出す。

        マウスのイベントの中のエラーは、Maya が黙って捨てることがある (表示が更新されないだけに見える)。
        """
        if not getattr(self, "_ring_error_shown", False):
            self._ring_error_shown = True
            log.warning("輪切り ({}) でエラー:\n{}".format(where, traceback.format_exc()))

    def ringPress(self, pos, rays=None, projector=None, seam=False):
        self._ring_error_shown = False
        try:
            self._ring_press_body(pos, rays, projector, seam)
        except Exception:
            self._report_ring_error("押す")

    def _ring_press_body(self, pos, rays=None, projector=None, seam=False):
        """押した位置と、対象のメッシュの用意 (画面の位置・トポロジー) を覚える (カメラはドラッグの間は動かない)。

        rays(x, y) -> (始点, 向き) と projector(points) -> [(x, y) か None] はテストで渡す
        (省くと今のビューから)。
        """
        self.syncMesh()
        self._ring_press = pos
        self._ring_dragged = False
        self._ring_seam = bool(seam)   # 縦の継ぎ目 (Shift+ドラッグ。段階 21)
        if rays is None or projector is None:
            view = omui.M3dView.active3dView()
            rays = rays or (lambda x, y: _ray_tuple(view_ray(view, x, y)))
            projector = projector or (lambda points: project_points(view, points))
        self._ring_rays = rays
        self._ring_screens = []
        for target in self.targets.valid():
            try:
                prepared = RingTarget(target.model, projector(target.model.graph().points))
            except RuntimeError:
                continue   # メッシュが消えたなど
            self._ring_screens.append((target, prepared))

    def ringDrag(self, pos, drawMgr=None):
        """線を描き、ループを探してプレビューする。"""
        try:
            self._ring_drag_body(pos, drawMgr)
        except Exception:
            self._report_ring_error("ドラッグ")

    def _ring_drag_body(self, pos, drawMgr=None):
        if self._ring_press is None:
            return
        start = self._ring_press
        if not self._ring_dragged and max(abs(pos[0] - start[0]),
                                          abs(pos[1] - start[1])) < RING_DRAG_THRESHOLD:
            return
        if not self._ring_dragged:
            self._ring_kept = []   # 描き直し: 前のプレビューの微調整の用意は捨てる
        self._ring_dragged = True
        stroke = Stroke(start, pos)
        self.updateRing(stroke)
        if drawMgr is not None:
            draw_stroke(drawMgr, stroke.start, stroke.end)
            if self._manip is not None:
                # マニピュレータはドラッグ中に描き直されないので、プレビューもここに描く
                self._manip.renderRing(drawMgr)

    def ringRelease(self, pos):
        """離した: ドラッグならプレビューを残す。クリック (動かしていない) なら、プレビューを確定する。"""
        if self._ring_press is None:
            return None
        dragged = self._ring_dragged
        self._ring_press = None
        screens, self._ring_screens = self._ring_screens, []
        if dragged:
            self._ring_kept = screens   # 離したあとの微調整に使う (確定・捨てるまで)
            if self._ring_found is not None and self.settings.value("ringSmooth") \
                    and not self._ring_seam:
                self._refine_ring(screens)   # 離したときだけ、なめらかにする (段階 20)
            if self._ring_found is None:
                log.info("線がメッシュを横切っていません (輪切りのエッジがありません)")
            else:
                how = {"loop": "今あるループ", "smooth": "なめらかにした道", "section": "境目",
                       "seam": "縦の継ぎ目"}.get(self._ring_found[1].method, "")
                log.info("輪切りのプレビュー {} 本 ({}。{})。クリックで確定、ホイールでずらす、"
                         "Shift+ホイールで傾ける、Esc で捨てる".format(
                             len(self._ring_found[1].edges), how, self._ring_found[0].name()))
            self._redraw()   # 残ったプレビューをマニピュレータで描く (ドラッグ中はツールの描画だった)
            return None
        segment = self.confirmRing()
        self._redraw()
        return segment

    def _refine_ring(self, screens):
        """プレビューを、なめらかにしたもの (今あるループ / 引き直した道) に置き換える。"""
        target, found = self._ring_found
        prepared = next((p for t, p in screens if t is target), None)
        if prepared is None or self._ring_stroke is None:
            return
        try:
            better = prepared.refine(self._ring_plane, self._ring_stroke, found)
        except RuntimeError:
            return   # メッシュが消えたなど
        if better is not found:
            self._ring_found = (target, better)
            self._update_ring_preview()

    # -- 探す・見せる ----------------------------------------------------------------

    def findRing(self, stroke):
        """切る面の境目 (メッシュ, RingFound)。線が複数のメッシュにかかれば、エッジのいちばん多いもの。

        線の両端の視線 2 本で切る面を作り (core.section.plane_from_rays)、メッシュごとに境目を求める。
        無ければ (None, None)。
        """
        if stroke.length < MIN_LENGTH:
            return None, None
        start_ray = self._ring_rays(*stroke.start)
        plane = plane_from_rays(start_ray, self._ring_rays(*stroke.end))
        self._ring_plane = plane
        self._ring_view = tuple(start_ray[1])
        seam_view = self._ring_view if self._ring_seam else None
        best = (None, None)
        for target, prepared in self._ring_screens:
            found = prepared.find(plane, stroke, seam_view)
            if found is not None and (best[1] is None or len(found.edges) > len(best[1].edges)):
                best = (target, found)
        return best

    def updateRing(self, stroke):
        """プレビューを探し直す (同じ線なら何もしない)。"""
        if self._ring_stroke is not None and self._ring_stroke.key() == stroke.key():
            return
        self._ring_stroke = stroke
        target, found = self.findRing(stroke)
        self._ring_found = (target, found) if found is not None else None
        self._update_ring_preview()

    def _update_ring_preview(self):
        """マニピュレータに、プレビューのループ (と、対称なら反対側) を渡す。"""
        if self._manip is None:
            return
        items = draw_list.DrawList()
        if self._ring_found is not None:
            target, found = self._ring_found
            graph = target.model.graph()
            label = ("縦の継ぎ目 {} 本".format(len(found.edges)) if found.method == "seam" else "")
            items.extend(draw_list.ring_items(graph, found.edges, label))
            mirror = self.mirrorFor(target)
            if mirror is not None:
                mirrored = [e for e in mirror.edges(found.edges)[0] if e not in set(found.edges)]
                items.extend(draw_list.mirror_items(graph, mirrored))
        self._manip.setRingPreview(items)

    def clearRing(self):
        """プレビューを捨てる。捨てたら True。"""
        had = self._ring_found is not None
        self._ring_found = None
        self._ring_stroke = None
        self._ring_press = None
        self._ring_screens = []
        self._ring_kept = []
        if had:
            self._update_ring_preview()
        return had

    # -- 微調整 (段階 21) -----------------------------------------------------------------

    def onWheel(self, delta, shift=False, ctrl=False):
        """ビューのホイール (tool/keys.py から)。輪切りのプレビューがあれば微調整して True (Maya に渡さない)。"""
        if self.mode() != MODE_RING or self._ring_found is None or not self._ring_kept or not delta:
            return False
        self.adjustRing(1 if delta > 0 else -1, tilt=shift)
        return True

    def adjustRing(self, steps, tilt=False):
        """プレビューを、ずらす (面を法線の向きに 平均のエッジの長さ x steps) か、傾ける (TILT_DEGREES x steps)。

        同じメッシュで境目を求め直し (なめらかにする設定なら整え直す)、プレビューを置き換える。
        求め直せなければ (メッシュから外れた) 今のまま。変えたら True。
        """
        if self._ring_found is None or self._ring_plane is None:
            return False
        target, found = self._ring_found
        prepared = next((p for t, p in self._ring_kept if t is target), None)
        if prepared is None:
            return False
        graph = target.model.graph()
        if tilt:
            vertices = set(v for e in found.edges for v in graph.edges[e])
            center = tuple(sum(graph.points[v][k] for v in vertices) / len(vertices) for k in range(3))
            plane = tilt_plane(self._ring_plane, self._ring_view, TILT_DEGREES * steps, center)
        else:
            step = sum(graph.lengths) / len(graph.lengths) if graph.lengths else 0.0
            plane = shift_plane(self._ring_plane, step * steps)
        seam_view = self._ring_view if self._ring_seam else None
        try:
            moved = prepared.find(plane, self._ring_stroke, seam_view)
            if moved is not None and not self._ring_seam and self.settings.value("ringSmooth"):
                moved = prepared.refine(plane, self._ring_stroke, moved)
        except RuntimeError:
            return False
        if moved is None:
            log.info("これ以上動かすと、メッシュから外れます")
            return False
        self._ring_plane = plane
        self._ring_found = (target, moved)
        self._update_ring_preview()
        self._redraw()
        return True

    # -- 確定 -----------------------------------------------------------------------

    def confirmRing(self):
        """プレビューのループを区間として積む (ためる。自動カットなら実行も。1 回の Undo)。PathSegment か None。"""
        if self._ring_found is None:
            return None
        target, found = self._ring_found
        if not target.isValid():
            self.clearRing()
            return None
        session = target.session(create=True)
        operation = (self.settings.value("operation") if self.settings.value("autoCut") else None)
        blocker = scene_mesh.edit_blocker(target.name()) if operation else None
        if blocker:
            log.warning("{}: {}。確定だけして、{}はしません".format(
                target.name(), blocker, OPERATION_LABELS[operation]))
            operation = None
        mirror = self.mirrorFor(target)
        name = "縦の継ぎ目" if found.method == "seam" else "輪切り"
        segment = self._run_edit("{}の確定".format(name), scene_edit.confirm_ring, session,
                                 target.name(), found.edges, operation,
                                 others=self._other_edges(target), mirror=mirror,
                                 title="UV {}の確定".format(name))
        self.clearRing()
        if segment is not None:
            log.info("{} {} 本を確定しました ({}){}".format(
                name, len(found.edges), target.name(),
                "  反対側 {} 本".format(len(segment.mirror_edges)) if segment.mirror_edges else ""))
            if segment.mirror_missing:
                log.warning("反対側が見つからないエッジが {} 本あります (その分は片側だけ)".format(
                    segment.mirror_missing))
        return segment


def diagnose(start=None, end=None):
    """(調べる用) 今のビューで輪切りの各段階の数をスクリプトエディタに出す。GUI で呼ぶ。

    start / end を省くと、ビューの真ん中に、上の端から下の端までの縦の線を引いたとする。
    対象は選んでいる / ハイライトしているメッシュ。
    """
    from ..core.section import plane_from_rays, section_edges
    from ..scene.mesh import MeshModel, target_meshes
    from ..scene.ring import RingTarget
    view = omui.M3dView.active3dView()
    width, height = view.portWidth(), view.portHeight()
    start = start or (width * 0.5, height * 0.9)
    end = end or (width * 0.5, height * 0.1)
    stroke = Stroke(start, end)
    rays = [_ray_tuple(view_ray(view, *point)) for point in (stroke.start, stroke.end)]
    plane = plane_from_rays(*rays)
    print("ビュー {} x {}  線 {} -> {}  カメラ {}".format(
        width, height, stroke.start, stroke.end, cmds.modelEditor(cmds.getPanel(withFocus=True),
                                                                    query=True, camera=True)
        if cmds.getPanel(typeOf=cmds.getPanel(withFocus=True) or "") == "modelPanel" else "?"))
    print("視線 {}".format(rays))
    print("切る面 {}".format(plane))
    for shape in target_meshes():
        model = MeshModel(shape)
        try:
            screen = project_points(view, model.graph().points)
            visible = sum(1 for p in screen if p is not None)
            prepared = RingTarget(model, screen)
            edges = section_edges(prepared.topology, prepared.points, plane, prepared.screen, stroke)
            everything = section_edges(prepared.topology, prepared.points, plane, prepared.screen,
                                       Stroke((stroke.start[0], -1.0e6), (stroke.end[0], 1.0e6)))
            print("{}: 頂点 {} (画面に写る {})  境目 (線の範囲) {} 本 / (線の延長も) {} 本".format(
                shape, len(screen), visible, len(edges), len(everything)))
            print("  画面の位置の例 {}".format([screen[i] for i in range(0, len(screen),
                                                                      max(1, len(screen) // 5))]))
        finally:
            model.release()
