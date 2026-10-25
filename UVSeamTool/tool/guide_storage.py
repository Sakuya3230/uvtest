"""
ガイドの組を、メッシュのシェイプのアトリビュートから読む / に書く (JSON とトポロジーの確かめ)。
"""

from ..core.guide import guide_json
from ..core.guide.guide_set import GuideSet
from ..utils import guide_attribute, log


def load(mesh, topology):
    """mesh に保存したガイドの組。無い・読めない・トポロジーが違えば空の組 (アトリビュートは書き換えない)。

    トポロジーが違うときは使わずに残す (ユーザーの決定)。Undo でトポロジーを戻せば、また使える。
    新しいガイドを作ると、そのときの組で上書きする。
    """
    text = guide_attribute.read_text(mesh)
    if not text:
        return GuideSet()

    try:
        guide_set, saved_topology = guide_json.loads(text)
    except ValueError as error:
        log.warning("{}: 保存したガイドを読めません ({})。ガイドなしとして扱います".format(mesh.name(), error))
        return GuideSet()

    if saved_topology != topology:
        log.warning("{}: 保存したときとトポロジーが違うので、保存したガイド ({} 本) は使いません。"
                    "新しいガイドを作ると上書きします".format(mesh.name(), len(guide_set.guides)))
        return GuideSet()

    log.debug("{}: 保存したガイドを {} 本読みました".format(mesh.name(), len(guide_set.guides)))

    return guide_set


def guides_text(target, guide_set):
    """target (TargetMesh) に保存する、ガイドの組の文字列 (トポロジーの目印と、点ごとの控えの位置も)。

    編集したときに 1 回だけ作る (Undo / Redo ではこの文字列をそのまま書く。あとでトポロジーが変わっていても、
    編集したときの位置のまま)。
    """
    return guide_json.dumps(guide_set, target.topology(), lambda point: target.pointPositions([point], world=False)[0])


def save_text(mesh, text):
    """アトリビュートに文字列をそのまま書く (None ならアトリビュートを消す)。書けなければ警告するだけ。"""
    if not mesh.isValid():
        return

    if mesh.isShapeLocked():
        # 書けない (対象にしたときに tool.mesh_checks が知らせてあるので、編集のたびには警告しない)
        log.debug("{}: シェイプがロックされているので、ガイドを保存しません".format(mesh.name()))
        return

    try:
        if text is None:
            guide_attribute.delete(mesh)
        else:
            guide_attribute.write_text(mesh, text)
    except RuntimeError as error:
        log.warning("{}: ガイドを保存できません ({})".format(mesh.name(), error))
