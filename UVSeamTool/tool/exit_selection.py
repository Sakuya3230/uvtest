"""
ツールを抜けるときに、ガイドのエッジを Maya の選択にする。
"""

from ..core.seam.seam import seam_edges
from ..core.settings import settings
from ..utils import log
from ..utils.selection import REPLACE, enter_edge_mode, select_edges


def select_guides(targets):
    """対象のメッシュの確定したガイドすべてのエッジを、エッジの選択モードで選ぶ (選択は置き換え)。

    設定 selectGuidesOnExit がオフ・ガイドが 1 本も無いときは、選択を変えない。
    """
    if not settings.current().value("selectGuidesOnExit"):
        return

    items = []
    for target in targets:
        mesh = target.mesh()
        if not mesh.isValid():
            continue

        guide_set = target.guideSet()
        guides    = [guide for guide in guide_set.guides if guide.id != guide_set.active_id]
        edges     = sorted({edge for guide in guides for edge in seam_edges(guide, target.graph())})
        if edges:
            items.append((mesh, edges))

    if not items:
        return

    enter_edge_mode([mesh for mesh, _ in items])
    select_edges(items, REPLACE)
    log.info("ガイドのエッジを選びました ({} 本)".format(sum(len(edges) for _, edges in items)))
