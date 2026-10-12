# -*- coding: utf-8 -*-
"""
描画の補助 (ビューのレイ・色・MPoint への変換)。

段階 3:
    source, direction = view_ray(view, x, y)       # ピクセルを通るワールドのレイ
    color = display_color((1, 0.5, 0), key)         # 画面にその色で見せるために渡す値
段階 6:
    render(drawMgr, draw_list, eye, key)            # core.draw_list.DrawList を描く
段階 10:
    plane = ScreenPlane(view, depth)                # 画面のピクセルを 3D に戻す (押せる部品のため)
    render_panel(drawMgr, plane, layout, ...)        # ビューのボタン (押せる部品 + 文字)

カラーマネジメント:
    カラーマネジメントが有効 (2022 / 2027 の既定) だと、マニピュレータの 3D の部品の色は
    シーンリニアの値として表示の変換 (既定は ACES 1.0 SDR-video) を通って画面に出る。
    青 (0.27, 0.62, 1.0) がシアンに、0.16 の灰色が 0.33 に見えた (ウェイトスライダーで確認)。
    cmds.colorManagementConvert(toDisplaySpace=) が「渡す値 -> 表示の色」なので、その逆を
    二分法で求める。ACES はチャンネルどうしが影響し合う (青を強くすると赤の表示が 0 に
    張り付くなど) ので、1 チャンネルずつ、ほかを固定して合わせることを全体が合うまで繰り返す
    (1 色あたり 200〜300 回の変換。結果は覚えておくので最初の 1 回だけ)。
    文字 (text / text2d) の色は変換されないように見えた (ウェイトスライダー)。
"""
import maya.api.OpenMaya as om
import maya.api.OpenMayaRender as omr
import maya.cmds as cmds

from ..core import accel
from ..core.draw_list import LINES, LOOP, POINT, TEXT, THEME, TRIANGLES
from ..core.geometry import toward

__all__ = ["view_ray", "view_projector", "color_management_key", "display_color", "mpoint",
           "mpoints", "render", "EYE_OFFSET", "ScreenPlane", "render_panel", "PLANE_NEAR_RATIO",
           "project_points", "draw_marquee", "draw_stroke"]

PLANE_NEAR_RATIO = 1.5   # ボタンの平面の距離 (カメラのニアクリップに対する倍率)
BUTTON_FONT_SIZE = 11

EYE_OFFSET = 0.002   # 描く点をカメラへ寄せる量 (カメラまでの距離に対する割合。Style.layer 倍)

# 表示の色 -> 渡す値 の変換の結果。キーは (カラーマネジメントの設定, 表示の色)
_DISPLAY_COLOR_CACHE = {}


def view_ray(view, x, y):
    """ビューのピクセル (x, y) を通るワールドのレイ (始点 MPoint, 向き MVector)。

    M3dView.viewToWorld は結果を渡した変数に書く (戻り値ではない)。
    """
    source = om.MPoint()
    direction = om.MVector()
    view.viewToWorld(int(x), int(y), source, direction)
    return source, direction


def view_projector(view):
    """ワールドの点 (タプル) を、ビューの画面のピクセル (x, y) へ投影する関数 (段階 4)。

    core.picking.pick_component に渡す。M3dView.worldToView は (x, y, クリップされていないか) を返す。
    """
    def project(point):
        x, y, _visible = view.worldToView(om.MPoint(point[0], point[1], point[2]))
        return x, y
    return project


def project_points(view, points):
    """たくさんのワールドの点 (タプル) を、ビューの画面のピクセル (x, y) へ。カメラの後ろは None (段階 16d)。

    矩形選択でメッシュの全頂点を投影する。worldToView を 1 点ずつ呼ぶと遅いので、numpy があれば
    モデルビュー行列 x 射影行列でまとめて計算する (Maya の行列は行ベクトル: p * MV * P)。
    行列の読み違いに備えて、最初の数点を worldToView と比べ、1 ピクセルより違えば 1 点ずつの計算に戻す。
    """
    modules = accel.scipy_modules()
    if modules is not None and points:
        np = modules[0]
        width, height = view.portWidth(), view.portHeight()
        matrix = np.array(list(view.modelViewMatrix()), dtype=np.float64).reshape(4, 4).dot(
            np.array(list(view.projectionMatrix()), dtype=np.float64).reshape(4, 4))
        coords = np.asarray(points, dtype=np.float64).reshape(-1, 3)
        clip = np.hstack([coords, np.ones((len(coords), 1))]).dot(matrix)
        w = clip[:, 3]
        safe = np.where(w > 1e-9, w, 1.0)
        xs = (clip[:, 0] / safe * 0.5 + 0.5) * width
        ys = (clip[:, 1] / safe * 0.5 + 0.5) * height
        visible = w > 1e-9
        ok = True
        for index in range(min(4, len(points))):
            if not visible[index]:
                continue
            x, y, _clipped = view.worldToView(om.MPoint(*points[index]))
            if abs(x - xs[index]) > 1.0 or abs(y - ys[index]) > 1.0:
                ok = False
                break
        if ok:
            return [(float(x), float(y)) if v else None
                    for x, y, v in zip(xs.tolist(), ys.tolist(), visible.tolist())]
    result = []
    for point in points:
        x, y, visible = view.worldToView(om.MPoint(point[0], point[1], point[2]))
        result.append((x, y) if visible else None)
    return result


def draw_marquee(drawMgr, rect):
    """矩形選択の枠 (画面の 2D の線)。コンテキストの doDrag の drawMgr に描く (段階 16d)。"""
    left, bottom, right, top = rect
    drawMgr.beginDrawable()
    drawMgr.setColor(om.MColor((0.9, 0.9, 0.9, 1.0)))
    drawMgr.setLineStyle(omr.MUIDrawManager.kDashed)
    corners = [(left, bottom), (right, bottom), (right, top), (left, top)]
    for (x0, y0), (x1, y1) in zip(corners, corners[1:] + corners[:1]):
        drawMgr.line2d(om.MPoint(x0, y0), om.MPoint(x1, y1))
    drawMgr.endDrawable()


def draw_stroke(drawMgr, start, end):
    """輪切りの線 (画面の 2D の線)。コンテキストの doDrag の drawMgr に描く (段階 19)。"""
    drawMgr.beginDrawable()
    drawMgr.setColor(om.MColor((1.0, 1.0, 1.0, 1.0)))
    drawMgr.setLineWidth(2.0)
    drawMgr.line2d(om.MPoint(start[0], start[1]), om.MPoint(end[0], end[1]))
    drawMgr.endDrawable()


def color_management_key():
    """今のカラーマネジメントの設定 (変わったら変換をやり直すためのキー)。無効なら None。"""
    try:
        if not cmds.colorManagementPrefs(query=True, cmEnabled=True):
            return None
        return cmds.colorManagementPrefs(query=True, viewTransformName=True)
    except RuntimeError:
        return None


def display_color(rgb, key):
    """画面に rgb (表示の色) で見せるために、drawMgr.setColor に渡す値 (r, g, b)。

    key は color_management_key() (描くたびに 1 回だけ問い合わせて渡す)。None なら変換しない。
    届かない色 (明るすぎる色) は、範囲の端の近い色になる。
    """
    if key is None:
        return tuple(rgb)
    cache_key = (key, tuple(rgb))
    if cache_key in _DISPLAY_COLOR_CACHE:
        return _DISPLAY_COLOR_CACHE[cache_key]
    value = [max(c, 1e-3) ** 2.2 for c in rgb]   # 初めの値 (sRGB のガンマの逆で近い所から)
    for _sweep in range(8):
        for i in range(3):
            low, high = 0.0, 16.0
            for _ in range(30):
                trial = list(value)
                trial[i] = (low + high) / 2.0
                if cmds.colorManagementConvert(toDisplaySpace=trial)[i] < rgb[i]:
                    low = trial[i]
                else:
                    high = trial[i]
            value[i] = (low + high) / 2.0
        shown = cmds.colorManagementConvert(toDisplaySpace=value)
        if max(abs(s - t) for s, t in zip(shown, rgb)) < 1e-3:
            break
    result = tuple(value)
    _DISPLAY_COLOR_CACHE[cache_key] = result
    return result


def mpoint(xyz):
    return om.MPoint(xyz[0], xyz[1], xyz[2])


def mpoints(points):
    """タプルのリストを MPointArray にする (drawMgr.mesh などに渡す)。"""
    return om.MPointArray([om.MPoint(p[0], p[1], p[2]) for p in points])


def _merged(items):
    """続いている同じ役割の LINES / TRIANGLES を 1 つにまとめる (MUIDrawManager の呼び出しを減らす)。"""
    merged = []
    for item in items:
        last = merged[-1] if merged else None
        if (last is not None and item.kind in (LINES, TRIANGLES) and last[0] == item.kind
                and last[1] == item.role):
            last[2].extend(item.points)
        else:
            merged.append([item.kind, item.role, list(item.points), item.text])
    return merged


def render(drawMgr, draw_list, eye, cm_key, colors=None):
    """描画の一覧 (core.draw_list.DrawList) を MUIDrawManager で描く (段階 6)。

    - 点は役割の Style.layer に合わせてカメラへ寄せる (面に重ねてもちらつかないように。
      寄せる量はカメラまでの距離に比例するので、遠くでも近くでも効く)
    - 色はカラーマネジメントの逆変換 (display_color) を通す。文字の色は変換されないのでそのまま
    - 押せない部品 (kNonSelectable) として描くので、クリックは普通の選択 / コンテキストに届く
    - colors ({役割: 色}。色の設定。core.draw_list.theme_colors) があれば、THEME の色の代わりに使う
    """
    if not draw_list.items:
        return
    drawMgr.beginDrawable(omr.MUIDrawManager.kNonSelectable, 0)
    for kind, role, points, text in _merged(draw_list.items):
        style = THEME[role]
        color = tuple((colors or {}).get(role, style.color))
        moved = [toward(p, eye, EYE_OFFSET * style.layer) for p in points]
        if kind == TEXT:
            drawMgr.setColor(om.MColor(color + (style.alpha,)))
            drawMgr.text(mpoint(moved[0]), text, omr.MUIDrawManager.kLeft)
            continue
        r, g, b = display_color(color, cm_key)
        drawMgr.setColor(om.MColor((r, g, b, style.alpha)))
        if kind == POINT:
            drawMgr.setPointSize(style.size)
            drawMgr.point(mpoint(moved[0]))
        elif kind == LINES:
            drawMgr.setLineWidth(style.width)
            drawMgr.mesh(omr.MUIDrawManager.kLines, mpoints(moved))
        elif kind == LOOP:
            drawMgr.setLineWidth(style.width)
            drawMgr.mesh(omr.MUIDrawManager.kClosedLine, mpoints(moved))
        elif kind == TRIANGLES:
            drawMgr.mesh(omr.MUIDrawManager.kTriangles, mpoints(moved))
    drawMgr.endDrawable()


class ScreenPlane(object):
    """画面のピクセルを、カメラの視線に垂直な平面の上のワールドの点に戻す (段階 10)。

    2D で描いたもの (rect2d など) はマニピュレータのハンドルにならない (押せない。ウェイトスライダーで
    確認)。押せる部品は、画面で決めた形の角を、それぞれのピクセルを通るレイとこの平面の交点として
    ワールドに戻し、3D で描く。画面ではちょうど決めた形に見える (透視でも平行投影でも)。
    平面は画面の中央を通るレイの上、depth の距離に置く。カメラのニアクリップのすぐ奥にすれば、
    手前のメッシュに隠れない。
    """

    def __init__(self, view, depth):
        self.view = view
        source, direction = view_ray(view, view.portWidth() / 2.0, view.portHeight() / 2.0)
        self.normal = direction.normal()
        self.center = source + self.normal * depth

    def point(self, x, y):
        source, direction = view_ray(self.view, x, y)
        denom = direction * self.normal   # MVector 同士の * は内積
        if abs(denom) < 1e-12:
            return om.MPoint(self.center)
        t = ((self.center - source) * self.normal) / denom
        return source + direction * t


def render_panel(drawMgr, plane, layout, buttons, first_handle, cm_key):
    """ビューのボタンを描く (段階 10)。

    buttons は [(操作の ID, 文字, 押せるか, 状態の名前 (core.panel.BUTTON_COLORS のキー))]
    (見えるボタンだけ)。四角は押せる部品 (kSelectable)。ハンドルの名前は first_handle + 表の番号
    (core.actions.action_index。モードで見えるボタンが変わっても、ボタンの見分けは変わらない)。
    文字は 2D (text2d。押せない部品) で重ねる。
    """
    from ..core.actions import action_index
    from ..core.panel import BUTTON_COLORS, TEXT_COLORS
    for action_id, _text, _enabled, state in buttons:
        index = action_index(action_id)
        left, bottom, right, top = layout[action_id]
        corners = [plane.point(x, y) for x, y in
                   ((left, bottom), (right, bottom), (right, top), (left, top))]
        drawMgr.beginDrawable(omr.MUIDrawManager.kSelectable, first_handle + index)
        r, g, b = display_color(BUTTON_COLORS[state], cm_key)
        drawMgr.setColor(om.MColor((r, g, b, 1.0)))
        drawMgr.mesh(omr.MUIDrawManager.kTriangles, om.MPointArray(
            [corners[0], corners[1], corners[2], corners[0], corners[2], corners[3]]))
        drawMgr.endDrawable()
    drawMgr.beginDrawable(omr.MUIDrawManager.kNonSelectable, 0)
    drawMgr.setFontSize(BUTTON_FONT_SIZE)
    for action_id, text, enabled, _state in buttons:
        left, bottom, right, top = layout[action_id]
        drawMgr.setColor(om.MColor(TEXT_COLORS[bool(enabled)] + (1.0,)))
        drawMgr.text2d(om.MPoint((left + right) / 2.0, (bottom + top) / 2.0 - 5), text,
                       omr.MUIDrawManager.kCenter)
    drawMgr.endDrawable()
