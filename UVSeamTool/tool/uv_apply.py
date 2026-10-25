"""
ガイドのエッジで UV をカット / 縫合する (ガイドは変えない)。
"""

from ..core.seam.seam import seam_edges
from ..core.symmetry.guide_mirror import with_partners
from ..utils import log, undo, uv_editor
from . import mesh_checks
from .symmetry import current_plane

CUT = "cut"
SEW = "sew"

_OPERATIONS = {CUT: (uv_editor.cut_edges, "カット"), SEW: (uv_editor.sew_edges, "縫合")}


def apply_guides(mesh, graph, guides, operation):
    """guides のエッジをまとめて、mesh の UV に operation (CUT / SEW) を当てる。当てたエッジの数を返す。"""
    if not guides:
        log.warning("{}するガイドがありません".format(_OPERATIONS[operation][1]))
        return 0

    edges = sorted({edge for guide in guides for edge in seam_edges(guide, graph)})

    return apply_edges(mesh, edges, operation, "ガイド {} 本".format(len(guides)))


def apply_edges(mesh, edges, operation, source=""):
    """エッジの番号の列を、mesh の UV に operation (CUT / SEW) で当てる。当てたエッジの数を返す。

    カット / 縫合できないメッシュ (シェイプのロックなど) は、警告して飛ばす (0 を返す)。
    source はログに出す元 (「ガイド 2 本」など。無ければエッジの数だけ)。
    """
    function, label = _OPERATIONS[operation]
    blocker = mesh_checks.edit_blocker(mesh)
    if blocker:
        log.warning("{}: {}。{}しません".format(mesh.name(), blocker, label))
        return 0

    function(mesh, edges)
    detail = "{} ({} 本のエッジ)".format(source, len(edges)) if source else "{} 本のエッジ".format(len(edges))
    log.info("{}: {}で{}しました".format(mesh.name(), detail, label))

    return len(edges)


def apply_selected_edges(items, operation):
    """[(Mesh, エッジの番号のリスト)] のメッシュごとに当てる (選択のモード)。全部で 1 回の Undo。"""
    items = [(mesh, edges) for mesh, edges in items if edges]
    if not items:
        log.warning("{}するエッジを選んでください".format(_OPERATIONS[operation][1]))
        return 0

    with undo.chunk(_OPERATIONS[operation][1]):
        return sum(apply_edges(mesh, edges, operation) for mesh, edges in items)


def apply_targets(items, operation):
    """[(TargetMesh, ガイドのリスト)] のメッシュごとに当てる。全部で 1 回の Undo。当てたエッジの数を返す。

    対称が効いていれば、ガイドの相手 (反対側のガイド) にも当てる。
    """
    if current_plane() is not None:
        items = [(target, with_partners(target.guideSet(), guides)) for target, guides in items]

    items = [(target, guides) for target, guides in items if guides]
    if not items:
        log.warning("{}するガイドがありません".format(_OPERATIONS[operation][1]))
        return 0

    with undo.chunk(_OPERATIONS[operation][1]):
        return sum(apply_guides(target.mesh(), target.graph(), guides, operation) for target, guides in items)
