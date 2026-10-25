"""
ビューに線と点を描く (MUIDrawManager を包む)。
"""

import maya.api.OpenMaya as om

from ..utils import view

_TOWARD_CAMERA = 0.002   # 面に重ねて描くとちらつくので、カメラへ距離の 0.2% 寄せる
_DOT_EXTRA     = 0.004   # 点はさらに寄せる (頂点の上の点が、同じ奥行きの線に隠れる・ちらつくため。線より手前に出す)


class Painter:
    """drawFeedback 1 回分の描き手。サブツールは MUIDrawManager を直接使わず、これに描かせる。

    点はワールドの (x, y, z)。色は (r, g, b) で、カラーマネジメントは考えない。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, draw_manager, frame_context):
        self._draw_manager  = draw_manager
        self._eye           = view.camera_position(frame_context)

    # -- 公開メソッド ---------------------------------------------------------
    def polyline(self, points, color, width=2.0):
        """点を順につないだ線。"""
        if len(points) < 2:
            return

        manager = self._draw_manager
        manager.beginDrawable()
        manager.setColor(om.MColor(color))
        manager.setLineWidth(width)
        manager.lineStrip(self._point_array(points), False)
        manager.endDrawable()

    def dots(self, points, color, size=8.0):
        """点の印。"""
        if not points:
            return

        manager = self._draw_manager
        manager.beginDrawable()
        manager.setColor(om.MColor(color))
        manager.setPointSize(size)
        manager.points(self._point_array(points, _DOT_EXTRA), False)
        manager.endDrawable()

    def segments(self, pairs, color, width=2.0):
        """線分 [(始点, 終点)] をまとめて描く (エッジを 1 本ずつ描くと遅いので、1 回の lineList で)。"""
        if not pairs:
            return

        points = [point for pair in pairs for point in pair]

        manager = self._draw_manager
        manager.beginDrawable()
        manager.setColor(om.MColor(color))
        manager.setLineWidth(width)
        manager.lineList(self._point_array(points), False)
        manager.endDrawable()

    def line2d(self, start, end, color):
        """画面の線分 (ピクセル (x, y) の 2 点。リングのドラッグの線)。"""
        manager = self._draw_manager
        manager.beginDrawable()
        manager.setColor(om.MColor(color))
        manager.setLineWidth(1.5)
        manager.lineStrip(om.MPointArray([om.MPoint(*start), om.MPoint(*end)]), True)   # True = 画面の座標で描く
        manager.endDrawable()

    def rect2d(self, rect, color):
        """画面の矩形 (左, 下, 右, 上。ピクセル) の枠 (矩形選択)。"""
        left, bottom, right, top = rect
        corners = [om.MPoint(left, bottom), om.MPoint(right, bottom), om.MPoint(right, top),
                   om.MPoint(left, top), om.MPoint(left, bottom)]

        manager = self._draw_manager
        manager.beginDrawable()
        manager.setColor(om.MColor(color))
        manager.setLineWidth(1.0)
        manager.lineStrip(om.MPointArray(corners), True)   # True = 画面の座標で描く
        manager.endDrawable()

    # -- 非公開メソッド -------------------------------------------------------
    def _point_array(self, points, extra=0.0):
        return om.MPointArray([self._toward_camera(point, extra) for point in points])

    def _toward_camera(self, point, extra=0.0):
        # extra: 線よりさらにカメラへ寄せる割合 (点)
        ex, ey, ez = self._eye
        t          = _TOWARD_CAMERA + extra
        x, y, z    = point

        return om.MPoint(x + (ex - x) * t, y + (ey - y) * t, z + (ez - z) * t)
