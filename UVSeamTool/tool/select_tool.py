"""
エッジを選んで、そのままカット / 縫合するサブツール (選択のモード)。ガイドは作らない。
"""

import maya.api.OpenMayaUI as omui

from ..utils import log
from ..utils.selection import (REPLACE, clear_selection, click_mode, double_click_mode, edges_in_rect, select_edges,
                               selected_edges)
from . import uv_apply
from .guide_drawing import color, draw_guides
from .select_picker import SelectPicker
from .sub_tool import SubTool
from .symmetry import current_plane

_MARQUEE_START  = 4.0    # 押してからこのピクセル以上動かしたら矩形選択 (それより短ければクリック)
_MARQUEE_COLOR  = (1.0, 1.0, 1.0)


class SelectTool(SubTool):
    """エッジを選ぶ。選んだ結果は Maya の選択に書く (cmds.select。Maya と同じく Undo に載る)。

    マウスの下のエッジを光らせ、クリックはその光っているエッジを選ぶ (光らせるのと選ぶのを同じ計算 SelectPicker.edgeAt で
    決めるので、食い違わない)。ダブルクリックは光っているエッジのループ (三角形も越える)。矩形は枠を自分で描き、離したときに
    Maya の矩形選択 (MGlobal.selectFromScreen。隠れたものは選ばない) で選ぶ。修飾キーは Maya と同じ。
    ループの事前ハイライト (setLoopHighlight。パネルのボタン・L キー) がオンの間は、マウスの下のループを光らせ、
    クリックでそのループを選ぶ。C / S = 選んでいる、対象のメッシュのエッジをカット / 縫合 (1 回の Undo)。
    左ボタンはすべて受け取る (Maya の事前選択・ダブルクリックの機能は使わない。どのモードにも効いてしまうため)。
    対称が効いているとき (tool.symmetry.current_plane) は、光らせる・選ぶのどれも反対側のエッジを足す
    (反対側が見つからないエッジは片側だけ)。反対側は mirrorColor で薄く光らせる。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, targets):
        self._targets           = targets
        self._picker            = SelectPicker(targets)
        self._loop_highlight    = False     # ループの事前ハイライトがオンか
        self._hovered           = None      # マウスの下の (TargetMesh, エッジ)
        self._lit               = None      # 光らせているエッジ (TargetMesh, エッジの番号のリスト)。クリックで選ぶもの
        self._press             = None      # 押した (x, y, shift, ctrl)
        self._marquee_rect      = None      # ドラッグ中の矩形 (左, 下, 右, 上)

    # -- 上書きするメソッド (SubTool) -----------------------------------------
    def deactivate(self):
        self._clear_hover()
        self.cancel()

    def targetChanged(self):
        self._clear_hover()   # エッジの番号・位置が変わっているかもしれない

    def hover(self, x, y):
        hovered = self._picker.edgeAt(x, y)
        if hovered == self._hovered:
            return False

        self._hovered = hovered
        self._update_lit()

        return True

    def draw(self, painter):
        for target in self._targets:
            draw_guides(painter, target)

        if self._lit is not None and self._press is None:
            target, edges = self._lit
            lit_color     = color("loopColor" if self._loop_highlight else "hoverEdgeColor")
            painter.segments(_edge_pairs(target, edges), lit_color, width=color("lineWidth"))
            mirrored      = _mirror_only(target, edges)
            if mirrored:
                painter.segments(_edge_pairs(target, mirrored), color("mirrorColor"),
                                 width=max(1.0, color("lineWidth") - 1.0))

        if self._marquee_rect is not None:
            painter.rect2d(self._marquee_rect, _MARQUEE_COLOR)

    def press(self, x, y, button, shift, ctrl):
        if button != omui.MEvent.kLeftMouse:
            return False

        self._press        = (x, y, shift, ctrl)
        self._marquee_rect = None

        return True

    def drag(self, x, y):
        if self._press is None:
            return False

        start_x, start_y, _, _ = self._press
        if self._marquee_rect is None and max(abs(x - start_x), abs(y - start_y)) < _MARQUEE_START:
            return False

        self._marquee_rect = (min(start_x, x), min(start_y, y), max(start_x, x), max(start_y, y))

        return True

    def release(self, x, y):
        if self._press is None:
            return False

        _, _, shift, ctrl = self._press
        rect              = self._marquee_rect
        self.cancel()

        if rect is not None:
            self._select_in_rect(rect, click_mode(shift, ctrl))
        elif self._lit is not None:
            target, edges = self._lit
            select_edges([(target.mesh(), _with_mirror(target, edges))], click_mode(shift, ctrl))
        elif not (shift or ctrl):
            clear_selection()   # 何も無い所をクリック

        return True

    def doubleClick(self, x, y, shift, ctrl):
        hovered = self._picker.edgeAt(x, y)
        if hovered is not None:
            target, edge = hovered
            edges        = target.edgeTopology().edgeLoop(edge, target.worldPoints())
            select_edges([(target.mesh(), _with_mirror(target, edges))], double_click_mode(shift, ctrl))
            log.debug("{}: ダブルクリックでループ ({} 本のエッジ) を選びました".format(target.mesh().name(), len(edges)))

        return True   # 何も無い所でも受け取る (Maya のダブルクリックの機能を動かさない)

    def isBusy(self):
        return self._press is not None

    def cancel(self):
        self._press        = None
        self._marquee_rect = None

    def applyOperation(self, operation):
        keys  = {target.key() for target in self._targets}
        items = [(mesh, edges) for mesh, edges in selected_edges() if mesh.key() in keys]
        uv_apply.apply_selected_edges(items, operation)

    # -- 公開メソッド ---------------------------------------------------------
    def loopHighlight(self):
        return self._loop_highlight

    def setLoopHighlight(self, enabled):
        self._loop_highlight = bool(enabled)
        self._update_lit()

    # -- 非公開メソッド -------------------------------------------------------
    def _select_in_rect(self, rect, mode):
        # Maya の矩形選択で矩形に入るエッジを求め、対象のメッシュなら反対側を足して、mode で 1 回に選ぶ
        items = []
        for mesh, edges in edges_in_rect(rect):
            target = self._targets.find(mesh.key())
            items.append((mesh, _with_mirror(target, edges) if target is not None else edges))

        if items:
            select_edges(items, mode)
        elif mode == REPLACE:
            clear_selection()   # 置き換えで矩形に何も無ければ、Maya と同じく選択を外す

    def _update_lit(self):
        # 光らせるエッジ (= クリックで選ぶもの) を決める。ループの事前ハイライトがオンならループ、オフならエッジ 1 本
        if self._hovered is None:
            self._lit = None
            return

        target, edge = self._hovered
        if self._loop_highlight:
            self._lit = (target, target.edgeTopology().edgeLoop(edge, target.worldPoints()))
        else:
            self._lit = (target, [edge])

    def _clear_hover(self):
        self._hovered = None
        self._lit     = None


def _edge_pairs(target, edges):
    # エッジの番号の列 -> 描く線分 [(始点, 終点)]
    topology = target.edgeTopology()

    return [tuple(target.positions(topology.edgeVertices(edge))) for edge in edges]


def _mirror_only(target, edges):
    # 対称が効いていれば、edges の反対側のうち edges に無いもの (無ければ空)
    plane = current_plane()
    if plane is None:
        return []

    mirrored, _ = target.mirrorMap(plane).edges(edges)

    return sorted(set(mirrored) - set(edges))


def _with_mirror(target, edges):
    # edges と、対称が効いていればその反対側 (重なりなし)
    return sorted(set(edges) | set(_mirror_only(target, edges)))
