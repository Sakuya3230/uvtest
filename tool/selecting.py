# -*- coding: utf-8 -*-
"""
選択のモードの選択 (段階 16d)。コンテキスト (tool/context.py) に組み込む部品 (ミックスイン)。

    selectClick(target, pick, op)      クリック (同じエッジを間隔の内に 2 回ならループ)
    selectLoop(target, pick, op)       ダブルクリックのループ (1 回目のクリックを取り消して 1 回の Undo)
    onDoubleClick(shift, ctrl)         Qt のダブルクリック (tool/keys.py のフィルターから)
    selectInRect(rect, op)             矩形 (一部でもかかる・表の面のエッジ)
    selectionMirrorEdges()             選んだエッジの反対側 (選んでいないもの)
    updateSelectionMirror()            その描く一覧をマニピュレータへ

コンテキストの属性 (targets・_manip・_clicks・_last_click・_last_loop・settings) と、ほかの部品の
メソッド (mirrorFor / symmetryActive は tool/symmetry.py、syncMesh / mode は context) を使う。
仕組みは core/selection.py と docs/16_select_mode.md。
"""
import time

import maya.api.OpenMayaUI as omui
import maya.cmds as cmds

from ..core import draw_list
from ..core.actions import MODE_SELECT
from ..core.mirror import with_mirror
from ..core.selection import REPLACE, loop_op, marquee_edges, selection_op
from ..scene import selection as scene_selection
from .drawing import project_points

__all__ = ["SelectingMixin", "MARQUEE_THRESHOLD", "event_position", "double_click_interval"]

MARQUEE_THRESHOLD = 4   # 選択のモード: この距離 (ピクセル) 以上ドラッグしたら矩形選択


def event_position(event):
    """MEvent の位置 (ビューのピクセル。左下が原点)。"""
    position = event.position
    return (position[0], position[1])


def double_click_interval():
    """ダブルクリックの間隔 (秒)。Qt の設定 (無ければ 0.5 秒)。"""
    try:
        from .keys import _qt
        qt = _qt()
        if qt is not None:
            return qt[1].QApplication.doubleClickInterval() / 1000.0
    except Exception:
        pass
    return 0.5


class SelectingMixin(object):
    """選択のモードの選択 (UVPathCutContext に組み込む)。"""

    # -- 選択のモードの選択 (段階 16d) -------------------------------------------------

    def _with_mirror(self, target, edges):
        """対称が効いていれば反対側も足したエッジ。"""
        return with_mirror(edges, self.mirrorFor(target))[0]

    def selectClick(self, target, pick, op, now=None):
        """クリック: 拾ったエッジを op で選ぶ。同じエッジのダブルクリックならループ。

        メッシュの外 (pick が None) は、置き換えなら選択を外す (Maya と同じ)。
        戻り値は選んだエッジ [(MeshTarget, [エッジ])]。
        """
        self.syncMesh()
        if pick is None or target is None:
            self._clicks.reset()
            if op == REPLACE:
                scene_selection.select_edges([], REPLACE)
            return []
        now = time.perf_counter() if now is None else now
        if self._clicks.click((target, pick.index), now):
            return self.selectLoop(target, pick, op, now)
        if self._recent_loop(target, pick, now):
            return []   # Qt のダブルクリックで選んだ直後の離し (同じダブルクリック)
        edges = self._with_mirror(target, [pick.index])
        scene_selection.select_edges([(target.name(), edges)], op)
        self._last_click = (target, pick.index, now, cmds.undoInfo(query=True, undoName=True))
        return [(target, edges)]

    def _undo_first_click(self, target, pick, now):
        """ダブルクリックの 1 回目のクリックの選択を取り消す (ダブルクリックを 1 回の Undo にするため)。

        直前の Undo が、同じエッジを間隔の内にクリックした、このツールの選択のときだけ取り消す
        (Undo の名前で確かめる。ほかの操作が間に入っていたら取り消さない)。
        """
        last, self._last_click = self._last_click, None
        if (last is None or last[0] is not target or last[1] != pick.index
                or now - last[2] > self._clicks.interval or not last[3]
                or cmds.undoInfo(query=True, undoName=True) != last[3]):
            return False
        cmds.undo()
        return True

    def _recent_loop(self, target, pick, now):
        last = self._last_loop
        return (last is not None and last[0] is target and last[1] == pick.index
                and now - last[2] <= self._clicks.interval)

    def selectLoop(self, target, pick, op, now=None):
        """ダブルクリック: 拾ったエッジからのループ (プレビューと同じ) を選ぶ。

        Qt のダブルクリック (onDoubleClick) と、押下が 2 回届いたとき (ClickTracker) の両方から呼ばれうるので、
        同じエッジを間隔の内に 2 回は選ばない。
        """
        now = time.perf_counter() if now is None else now
        if self._recent_loop(target, pick, now):
            return []
        self._last_loop = (target, pick.index, now)
        self._clicks.reset()
        self._undo_first_click(target, pick, now)   # 1 回目のクリックの選択は残さない (Undo が 1 回で済む)
        edges = self._with_mirror(target, target.model.edgeLoop(pick.index))
        scene_selection.select_edges([(target.name(), edges)], loop_op(op))
        return [(target, edges)]

    def onDoubleClick(self, shift, ctrl):
        """ビューの左ボタンのダブルクリック (tool/keys.py のフィルターから)。扱ったら True (Maya に渡さない)。"""
        if self.mode() != MODE_SELECT or self.targets is None or self._manip is None:
            return False
        self.syncMesh()
        target, pick = self._manip.pickTarget(), self._manip.pick()
        if target is not None and pick is not None:
            self.selectLoop(target, pick, selection_op(shift, ctrl))
        return True

    def selectInRect(self, rect, op, camera=None, projector=None):
        """矩形選択: 矩形の中に中点があり、表の面に付いているエッジを op で選ぶ (全メッシュ)。

        camera / projector はテストで渡す (省くと今のビューから)。projector(points) -> [(x, y) か None]。
        """
        self.syncMesh()
        self._clicks.reset()
        if camera is None or projector is None:
            view = omui.M3dView.active3dView()
            camera = camera or scene_selection.CameraInfo.fromView(view)
            projector = projector or (lambda points: project_points(view, points))
        pairs = []
        for target in self.targets.valid():
            graph = target.model.graph()
            positions = projector(graph.points)
            inside = marquee_edges([(e, a, b) for e, (a, b) in enumerate(graph.edges)], positions, rect)
            edges = scene_selection.front_edges(target.model, inside, camera)
            if edges:
                pairs.append((target.name(), self._with_mirror(target, edges)))
        scene_selection.select_edges(pairs, op)
        return pairs

    def selectionMirrorEdges(self):
        """選んでいるエッジの反対側 (選んでいないもの) [(MeshTarget, [エッジ])]。対称がオフなら []。"""
        if self.targets is None or not self.symmetryActive():
            return []
        result = []
        for target, edges in self.targets.selectedEdges()[0]:
            mirror = self.mirrorFor(target)
            if mirror is None:
                continue
            chosen = set(edges)
            others = [e for e in mirror.edges(edges)[0] if e not in chosen]
            if others:
                result.append((target, others))
        return result

    def updateSelectionMirror(self):
        """選択のモードで描く、選んだエッジの反対側を作り直す (選択・対称の設定が変わったとき)。"""
        if self._manip is None:
            return
        items = draw_list.DrawList()
        if self.mode() == MODE_SELECT:
            for target, edges in self.selectionMirrorEdges():
                items.extend(draw_list.mirror_items(target.model.graph(), edges))
        self._manip.setSelectionMirror(items)
