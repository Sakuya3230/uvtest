"""
扱えないメッシュ (ロック・インスタンス・UV なし) を調べて知らせる。
"""

from ..utils import log


def edit_blocker(mesh):
    """UV をカット / 縫合できない理由 (文)。できれば None。

    シェイプがロック (lockNode) されていると polyMapCut / polyMapSew は失敗し、理由が分かりにくいので前もって調べる。
    トランスフォームだけのロック・リファレンスのメッシュはカットできる (旧版で確認)。
    """
    if not mesh.isValid():
        return "メッシュがありません"

    if mesh.isShapeLocked():
        return "シェイプがロックされています (lockNode)"

    return None


def report(mesh):
    """対象にしたメッシュについて、知らせておくことをログに出す。"""
    instances = mesh.instanceCount()
    if instances > 1:
        log.info("{}: インスタンスです。カット / 縫合すると、ほかのインスタンス ({} 個) も同じに変わります".format(
            mesh.name(), instances - 1))

    if mesh.uvCount() == 0:
        log.warning("{}: UV がありません (カット / 縫合しても変わりません)".format(mesh.name()))

    blocker = edit_blocker(mesh)
    if blocker:
        log.warning("{}: {}。ガイドは作れますが、カット / 縫合とガイドの保存はできません".format(mesh.name(), blocker))
