"""
ボタンのアイコンを QPainter で描く (画像のファイルを使わない)。

    draw_icon(painter, name, rect, color)   name のアイコンを rect の中に color で描く (知らない名前なら何も描かない)

アイコンを足すときは、描く関数を書いて _ICONS に 1 行足す。
"""

from ..compat.qt import QtCore, QtGui


def draw_icon(painter, name, rect, color):
    function = _ICONS.get(name)
    if function is None:
        return

    painter.save()
    pen = QtGui.QPen(color, max(1.5, rect.width() * 0.08))
    pen.setCapStyle(QtCore.Qt.RoundCap)
    pen.setJoinStyle(QtCore.Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(QtCore.Qt.NoBrush)
    function(painter, rect, color)
    painter.restore()


def _point(rect, u, v):
    # rect の中の割合 (u, v) の位置 (0 = 左 / 上、1 = 右 / 下)
    return QtCore.QPointF(rect.left() + rect.width() * u, rect.top() + rect.height() * v)


def _dot(painter, center, radius, color):
    painter.save()
    painter.setPen(QtCore.Qt.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(center, radius, radius)
    painter.restore()


def _create(painter, rect, color):
    # 点を 3 つ置いて線でつなぐ (ガイドを作る)
    points = [_point(rect, 0.12, 0.78), _point(rect, 0.45, 0.30), _point(rect, 0.88, 0.62)]
    painter.drawPolyline(QtGui.QPolygonF(points))
    for point in points:
        _dot(painter, point, rect.width() * 0.11, color)


def _edit(painter, rect, color):
    # 点を 1 つと、四方への矢印 (点を動かす)
    center = _point(rect, 0.5, 0.5)
    _dot(painter, center, rect.width() * 0.12, color)
    for u, v, du, dv in ((0.5, 0.06, 1, 0), (0.5, 0.94, 1, 0), (0.06, 0.5, 0, 1), (0.94, 0.5, 0, 1)):
        tip   = _point(rect, u, v)
        inner = _point(rect, 0.5 + (u - 0.5) * 0.45, 0.5 + (v - 0.5) * 0.45)
        painter.drawLine(inner, tip)
        side  = rect.width() * 0.12
        back  = QtCore.QPointF((inner.x() - tip.x()) * 0.35, (inner.y() - tip.y()) * 0.35)
        painter.drawLine(tip, tip + back + QtCore.QPointF(du * side, dv * side))
        painter.drawLine(tip, tip + back - QtCore.QPointF(du * side, dv * side))


def _cut(painter, rect, color):
    # はさみ (交わる 2 本の刃と、2 つの輪)
    painter.drawLine(_point(rect, 0.30, 0.62), _point(rect, 0.88, 0.10))
    painter.drawLine(_point(rect, 0.70, 0.62), _point(rect, 0.12, 0.10))
    radius = rect.width() * 0.15
    painter.drawEllipse(_point(rect, 0.25, 0.78), radius, radius)
    painter.drawEllipse(_point(rect, 0.75, 0.78), radius, radius)


def _sew(painter, rect, color):
    # 2 つの縁 (縦の線) を、斜めの縫い目でつなぐ
    painter.drawLine(_point(rect, 0.22, 0.08), _point(rect, 0.22, 0.92))
    painter.drawLine(_point(rect, 0.78, 0.08), _point(rect, 0.78, 0.92))
    for v in (0.22, 0.50, 0.78):
        painter.drawLine(_point(rect, 0.22, v + 0.10), _point(rect, 0.78, v - 0.10))


def _select(painter, rect, color):
    # 点線の矩形と、その中の 1 本の線 (エッジを選ぶ)
    pen = painter.pen()
    pen.setStyle(QtCore.Qt.DashLine)
    painter.setPen(pen)
    painter.drawRect(QtCore.QRectF(_point(rect, 0.08, 0.08), _point(rect, 0.92, 0.92)))
    pen.setStyle(QtCore.Qt.SolidLine)
    painter.setPen(pen)
    painter.drawLine(_point(rect, 0.28, 0.70), _point(rect, 0.72, 0.30))


def _loop(painter, rect, color):
    # 楕円 (ループ) と、マウスの矢印の先 (クリックでループを選ぶ)
    painter.drawEllipse(QtCore.QRectF(_point(rect, 0.06, 0.18), _point(rect, 0.94, 0.66)))
    tip = _point(rect, 0.55, 0.42)
    painter.drawLine(tip, _point(rect, 0.80, 0.95))
    painter.drawLine(tip, _point(rect, 0.55, 0.80))
    painter.drawLine(tip, _point(rect, 0.88, 0.60))


def _symmetry(painter, rect, color):
    # 点線の縦の軸と、左右に向き合う 2 つの三角形
    pen = painter.pen()
    pen.setStyle(QtCore.Qt.DashLine)
    painter.setPen(pen)
    painter.drawLine(_point(rect, 0.5, 0.0), _point(rect, 0.5, 1.0))
    pen.setStyle(QtCore.Qt.SolidLine)
    painter.setPen(pen)
    for side in (-1, 1):
        points = [_point(rect, 0.5 + side * 0.12, 0.2), _point(rect, 0.5 + side * 0.45, 0.5),
                  _point(rect, 0.5 + side * 0.12, 0.8)]
        painter.drawPolygon(QtGui.QPolygonF(points))


def _auto(painter, rect, color):
    # 稲妻 (すぐに当てる)
    points = [_point(rect, 0.62, 0.04), _point(rect, 0.22, 0.56), _point(rect, 0.50, 0.56),
              _point(rect, 0.38, 0.96), _point(rect, 0.78, 0.42), _point(rect, 0.50, 0.42)]
    painter.drawPolygon(QtGui.QPolygonF(points))


def _delete_all(painter, rect, color):
    # ごみ箱 (ふた・取っ手・箱と縦の線)
    painter.drawLine(_point(rect, 0.12, 0.22), _point(rect, 0.88, 0.22))
    painter.drawPolyline(QtGui.QPolygonF([_point(rect, 0.38, 0.22), _point(rect, 0.40, 0.08),
                                          _point(rect, 0.60, 0.08), _point(rect, 0.62, 0.22)]))
    painter.drawPolygon(QtGui.QPolygonF([_point(rect, 0.22, 0.30), _point(rect, 0.78, 0.30),
                                         _point(rect, 0.72, 0.94), _point(rect, 0.28, 0.94)]))
    for u in (0.40, 0.60):
        painter.drawLine(_point(rect, u, 0.42), _point(rect, u, 0.82))


_ICONS = {
    "create":    _create,
    "edit":      _edit,
    "select":    _select,
    "loop":      _loop,
    "symmetry":  _symmetry,
    "auto":      _auto,
    "cut":       _cut,
    "sew":       _sew,
    "deleteAll": _delete_all,
}
