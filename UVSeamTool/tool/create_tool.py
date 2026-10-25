"""
ガイドを作るサブツール (クリックした頂点を最短パスでつなぐ)。
"""

import maya.api.OpenMayaUI as omui

from ..core.guide import set_editing
from ..core.path.path_preview import PathPreview
from ..core.settings import settings
from ..utils import log
from . import auto_apply, guide_edit, uv_apply
from .guide_drawing import color, draw_guides
from .sub_tool import SubTool


class CreateTool(SubTool):
    """クリックで頂点に点を足してガイドを作る。点の間の区間は最短パス (設定「まっすぐさ」で曲がりの少ない道)。

    左クリック = 点を足す / Delete = 最後の点を消す / Esc = 作成中のガイドを捨てる /
    Enter・右クリック = ガイドを確定する (右クリックは作成中のガイドがあるときだけ。無ければマーキングメニュー)。
    どの操作もガイドの組 (core.guide.guide_store) を Undo できる 1 回の操作で変える (Ctrl+Z で 1 つずつ戻る)。
    マウスを動かすと、最後の点からマウスの下の頂点までの最短パスをプレビューする。
    カット / 縫合の対象は、作成中のガイド。設定の「自動」がオンなら、点を足すたびに足した区間へ当てる (tool.auto_apply)。
    確定せずに編集のモードへ替えた・ツールを抜けたときは、作成中のガイドを確定する。
    左ボタンはすべて受け取る (Maya の選択は使わない。編集のモードと同じ)。

    複数のメッシュ (tool.targets.Targets): 作成中のガイドは全体で 1 本。作成中に別のメッシュをクリックしたら、
    今のガイドを確定してから、そのメッシュで新しいガイドを始める。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, targets):
        self._targets       = targets
        self._path_previews = {}        # メッシュの鍵 -> PathPreview (そのメッシュのグラフの PathTree を使い回す)
        self._hover         = None      # マウスの下の (TargetMesh, 頂点)。無ければ None
        self._preview       = None      # 最後の点からマウスの下までの線のワールドの位置のリスト (無ければ None)

    # -- 上書きするメソッド (SubTool) -----------------------------------------
    def deactivate(self):
        # 作成中のガイドがあれば確定する (確定せずに編集のモードへ替えた・ツールを抜けたとき。Enter と同じ)
        self.complete()

        self._hover   = None
        self._preview = None

    def refresh(self):
        self._update_preview()

    def targetChanged(self):
        # グラフが作り直されたので、前のグラフの PathTree を捨てる。マウスの下の頂点も (番号が変わっているかもしれない)
        self._path_previews = {}
        self._hover         = None
        self._preview       = None

    def hover(self, x, y):
        target, vertex = self._targets.pick(x, y)
        hover          = (target, vertex) if target is not None else None
        if hover == self._hover:
            return False

        self._hover = hover
        self._update_preview()

        return True

    def draw(self, painter):
        for target in self._targets:
            draw_guides(painter, target)

        if self._preview is not None:
            painter.polyline(self._preview, color("previewColor"), width=max(1.0, color("lineWidth") - 1.0))

        if self._hover is not None:
            target, vertex = self._hover
            painter.dots(target.positions([vertex]), color("hoverVertexColor"), size=color("pointSize") - 2.0)

    def press(self, x, y, button, shift, ctrl):
        # 左ボタンはすべて受け取る (Maya の選択は使わない。メッシュの外・Shift 付きは何もしない)
        if button != omui.MEvent.kLeftMouse:
            return False

        if shift:
            return True

        target, vertex = self._targets.pick(x, y)
        if target is None:
            return True

        active_target, _ = self._active()
        if active_target is not None and active_target is not target:
            self.complete()   # 別のメッシュをクリックした: 今のガイドを確定してから、そのメッシュで始める

        new_set = set_editing.add_point(target.guideSet(), target.graph(), vertex)
        if new_set is None:
            log.warning("そこには点を足せません (最後の点と同じか、つながっていない)")
            return True

        auto_apply.add_point(target, new_set)
        log.debug("点を足しました: {} ({})".format(target.mesh().name(), self._points_text()))

        return True

    def doubleClick(self, x, y, shift, ctrl):
        # 受け取って何もしない (ダブルクリックを Maya に渡さない)
        return True

    def rightClick(self):
        # 作成中のガイドがあるときだけ確定する (無ければいつもどおりマーキングメニュー)
        if self._active()[0] is None:
            return False

        self.complete()

        return True

    def applyOperation(self, operation):
        target, active = self._active()
        items          = [(target, [active])] if active is not None and active.segments else []
        uv_apply.apply_targets(items, operation)

    def complete(self):
        target, active = self._active()
        if target is None:
            return

        new_set = set_editing.finish_active(target.guideSet())
        delete  = len(active.points) >= 2 and settings.current().value("deleteGuideOnComplete")
        if delete:
            # 確定と同時に消す (1 回の Undo で作成中に戻る。対称の相手も消える)
            new_set = set_editing.remove_guides(new_set, {active.id}) or new_set
        guide_edit.apply(target, new_set)
        if len(active.points) < 2:
            log.warning("点が 1 つだけのガイドは確定できないので捨てました")
        else:
            log.info("{}: ガイド {} を確定しました (点 {} つ{})".format(
                target.mesh().name(), active.id, len(active.points), "。設定により削除" if delete else ""))

    def abort(self):
        target, _ = self._active()
        if target is not None:
            guide_edit.apply(target, set_editing.discard_active(target.guideSet()))
            log.info("作成中のガイドを捨てました")

    def delete(self):
        target, _ = self._active()
        if target is not None:
            guide_edit.apply(target, set_editing.remove_last_point(target.guideSet()))
            log.debug("最後の点を消しました ({})".format(self._points_text()))

    # -- 非公開メソッド -------------------------------------------------------
    def _active(self):
        # 作成中のガイドがあるメッシュと、そのガイド (TargetMesh, Guide)。無ければ (None, None)
        for target in self._targets:
            active = set_editing.active_guide(target.guideSet())
            if active is not None:
                return target, active

        return None, None

    def _update_preview(self):
        # 作成中のガイドの最後の点か、マウスの下が変わったら呼ぶ。プレビューは同じメッシュの上だけ
        active_target, active = self._active()
        if active is None or self._hover is None or self._hover[0] is not active_target:
            self._preview = None
            return

        key = active_target.key()
        if key not in self._path_previews:
            self._path_previews[key] = PathPreview(active_target.graph())
        path          = self._path_previews[key].path(active.points[-1].vertex, self._hover[1])
        self._preview = active_target.positions(path) if path is not None else None

    def _points_text(self):
        _, active = self._active()
        if active is None:
            return "作成中のガイドなし"

        return "点 " + " -> ".join(str(point.vertex) for point in active.points)
