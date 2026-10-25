"""
ガイドを描く (作成と編集のサブツールで共通)。色は設定 (core.settings) から引く。
"""

from ..core.settings import settings


def color(key):
    """設定の値 (色 (r, g, b)・線の太さ・点の大きさ)。描くたびに引くので、設定を変えるとすぐ効く。"""
    return settings.current().value(key)


def draw_guides(painter, target, selected=frozenset(), hovered=None, replaced=None):
    """target (tool.target_mesh.TargetMesh) のガイドをすべて描く。

    作成中のガイドは色を変えて点も描く。selected (id の集合) は選んでいる色で太く、hovered (id) は明るく描く。
    replaced (GuideSet) があれば、target の組の代わりにそれを描く (ドラッグ中のプレビュー)。
    ガイドが通るエッジのうち UV の切れ目のもの (カット済み・メッシュの縁) は、その部分を cutColor (赤) で描く
    (ガイドは状態を持たないので、今の UV から求める。縫合済みとまだカットしていないものは、どちらも普通の色)。
    選んでいる・マウスの下のガイドは、どれを指しているかが見えるよう、切れ目の部分も選択の色のまま描く。
    """
    guide_set = replaced if replaced is not None else target.guideSet()
    for guide in guide_set.guides:
        active      = guide.id == guide_set.active_id
        width       = color("lineWidth")
        show_seams  = True
        if guide.id in selected:
            line_color, width, show_seams = color("selectedColor"), width + 1.0, False
        elif guide.id == hovered:
            line_color, show_seams = color("hoverGuideColor"), False
        elif active:
            line_color = color("activeColor")
        else:
            line_color = color("guideColor")

        for segment in guide.segments:
            if not show_seams:
                painter.polyline(target.positions(segment.seam), line_color, width=width)
                continue

            # 切れ目かどうかが同じエッジの続きごとに、1 回ずつ描く (重ねて描くと、同じ奥行きでちらつくため)
            for is_seam, run in _runs(target, segment.seam):
                painter.polyline(target.positions(run), color("cutColor") if is_seam else line_color, width=width)

        if active or guide.id in selected:
            painter.dots(target.pointPositions(guide.points), color("pointColor"), size=color("pointSize"))


def _runs(target, vertices):
    # 頂点の列を、UV の切れ目かどうかが同じエッジの続きに分ける。[(切れ目か, 頂点の列)] (隣どうしは端の頂点を共有)
    runs = []
    for a, b in zip(vertices, vertices[1:]):
        is_seam = target.isUVSeam(a, b)
        if runs and runs[-1][0] == is_seam:
            runs[-1][1].append(b)
        else:
            runs.append((is_seam, [a, b]))

    return runs
