"""
自動のカット / 縫合 (作成のモードで点を足すたびに、足した区間へ当てる)。
"""

from dataclasses import replace

from ..core.guide import set_editing
from ..core.seam.seam import seam_edges
from ..core.settings import settings
from ..utils import undo
from . import guide_edit, uv_apply
from .symmetry import current_plane


def add_point(target, new_set):
    """target のガイドの組を new_set (点を足した組) にする。自動がオンなら、足した区間にも当てる。

    点を足すのと当てるのは 1 回の Undo (Ctrl+Z で点とカットが一緒に戻る)。
    対称が効いていれば、相手のガイドの足した区間にも当てる (相手は guide_edit が作り直している)。
    """
    values = settings.current()
    if not values.value("autoApply"):
        guide_edit.apply(target, new_set)
        return

    operation = uv_apply.CUT if values.value("autoOperation") == "cut" else uv_apply.SEW
    with undo.chunk("点を足して自動で当てる"):
        guide_edit.apply(target, new_set)
        edges = _last_segment_edges(target)
        if edges:
            uv_apply.apply_edges(target.mesh(), edges, operation, "足した区間")


def _last_segment_edges(target):
    # 作成中のガイド (と、対称なら相手) の最後の区間のエッジ。最初の点だけなら空
    guide_set = target.guideSet()
    active    = set_editing.active_guide(guide_set)
    if active is None or not active.segments:
        return []

    guides = [active]
    if current_plane() is not None and active.partner is not None:
        partner = set_editing.find_guide(guide_set, active.partner)
        if partner is not None and partner.segments:
            guides.append(partner)

    edges = []
    for guide in guides:
        edges.extend(seam_edges(replace(guide, segments=(guide.segments[-1],)), target.graph()))

    return sorted(set(edges))
