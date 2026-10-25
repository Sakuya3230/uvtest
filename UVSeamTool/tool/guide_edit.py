"""
ガイドの組を変える (Undo できる 1 回の操作として)。
"""

from ..core.guide import guide_store
from ..core.symmetry.guide_mirror import sync_partners
from ..utils import guide_attribute, log, undo
from . import guide_storage
from .symmetry import current_plane


def apply(target, new_set):
    """target (tool.target_mesh.TargetMesh) のガイドの組を new_set にする。Ctrl+Z で前に戻る。"""
    apply_many([(target, new_set)])


def apply_many(items):
    """[(TargetMesh, 新しい組)] をまとめて 1 回の Undo で変える (複数のメッシュのガイドを一度に消すときなど)。

    置き場所 (guide_store) とシェイプのアトリビュートの両方を変える (Undo / Redo でも両方を書き戻す)。
    Undo ではアトリビュートの文字列を、操作の前のものにそのまま書き戻す (写しから作り直さない。トポロジーが違って
    使っていなかったガイドも、Undo すれば元の文字列に戻る)。
    対称が効いていれば、変えたガイドの相手 (反対側のガイド) も作り直す (同じ 1 回の Undo。core.symmetry.guide_mirror)。
    """
    plane   = current_plane()
    changes = []
    for target, new_set in items:
        mesh = target.mesh()
        if plane is not None:
            new_set = _with_partners(target, new_set, plane)
        changes.append((target, mesh, new_set,
                        guide_store.store().guideSet(target.key()),   # 前の組
                        guide_attribute.read_text(mesh),              # 前の文字列 (無ければ None。Undo でアトリビュートを消す)
                        guide_storage.guides_text(target, new_set),   # 後の文字列 (編集したときに 1 回だけ作る)
                        target.topology()))                           # 編集したときのトポロジー (Undo / Redo のときに比べる)

    def redo():
        for target, mesh, new_set, _, _, after_text, topology in changes:
            guide_storage.save_text(mesh, after_text)
            _set_store(target, topology, new_set)

    def restore():
        for target, mesh, _, before_set, before_text, _, topology in changes:
            guide_storage.save_text(mesh, before_text)
            _set_store(target, topology, before_set)

    if changes:
        undo.run(redo, restore)


def _with_partners(target, new_set, plane):
    # 前の組と比べて、変わったガイドの相手を作り直す
    mirror          = target.mirrorMap(plane)
    new_set, failed = sync_partners(guide_store.store().guideSet(target.key()), new_set, mirror.vertex)
    if failed:
        log.warning("{}: 反対側が見つからない頂点を通るガイドが {} 本あり、相手を作れませんでした".format(
            target.mesh().name(), failed))

    return new_set


def _set_store(target, topology, guide_set):
    # 置き場所 (表示に使う写し) を変えるのは、今のトポロジーが編集したときと同じときだけ
    # (トポロジーを変えたあとに前の編集を Undo すると、古い頂点の番号のガイドが新しいメッシュに出るため)
    if topology == target.topology():
        guide_store.store().setGuideSet(target.key(), guide_set)
