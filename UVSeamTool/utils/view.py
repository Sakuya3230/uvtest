"""
ビュー (M3dView) とカメラ。
"""

import maya.api.OpenMaya as om
import maya.api.OpenMayaRender as omr
import maya.api.OpenMayaUI as omui


def view_ray(x, y):
    """アクティブなビューのピクセル (x, y) を通るワールドのレイ (始点 MPoint, 向き MVector)。"""
    # M3dView.viewToWorld は結果を渡した変数に書く (戻り値ではない)
    source    = om.MPoint()
    direction = om.MVector()
    omui.M3dView.active3dView().viewToWorld(int(x), int(y), source, direction)

    return source, direction


def view_direction():
    """アクティブなビューのカメラの向き (ワールドの (x, y, z)。リングを傾ける軸を決める)。"""
    active = omui.M3dView.active3dView()
    width  = active.portWidth()
    height = active.portHeight()
    _, direction = view_ray(width // 2, height // 2)

    return direction.x, direction.y, direction.z


def world_to_view(points):
    """ワールドの点 (x, y, z) の列 -> アクティブなビューのピクセル (x, y) のリスト (左下が原点。MEvent と同じ)。"""
    active = omui.M3dView.active3dView()
    pixels = []
    for x, y, z in points:
        # worldToView は (x, y, クリップされていないか) を返す
        result = active.worldToView(om.MPoint(x, y, z))
        pixels.append((result[0], result[1]))

    return pixels


def refresh():
    """アクティブなビューの描き直しを頼む (コンテキストの drawFeedback が呼ばれる)。"""
    try:
        omui.M3dView.active3dView().refresh(False, True)
    except RuntimeError:
        pass   # ビューが無い (standalone など)


def camera_position(frame_context):
    """描いているビューのカメラのワールドの位置 (x, y, z)。"""
    matrix = frame_context.getMatrix(omr.MFrameContext.kViewInverseMtx)

    return (matrix.getElement(3, 0), matrix.getElement(3, 1), matrix.getElement(3, 2))


def active_view_pointer():
    """アクティブなビューの描画面のウィジェットのポインタ (数)。ビューが無ければ None。"""
    try:
        return int(omui.M3dView.active3dView().widget())
    except RuntimeError:
        return None   # ビューが無い (standalone など)


def view_widget_pointers():
    """3D のビューの描画面のウィジェットのポインタ (数) の集合 (マウスのイベントがビューのものか見分けるため)。

    M3dView.widget() は描画面 (QmayaGLWidget) の C++ のポインタを数で返す。
    """
    return {int(omui.M3dView.get3dView(index).widget()) for index in range(omui.M3dView.numberOf3dViews())}
