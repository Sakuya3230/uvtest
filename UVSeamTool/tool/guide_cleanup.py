"""
シーンに保存したガイドの一覧と削除 (ツール設定のウィンドウ・パネルの「全削除」・api から呼ぶ)。
"""

import maya.cmds as cmds

from ..core.guide import guide_json, guide_store
from ..core.guide.guide_set import GuideSet
from ..core.path.topology import topology_of
from ..utils import guide_attribute, log, undo
from . import guide_edit


def list_guides():
    """ガイドを保存しているメッシュごとの [{"mesh", "guides", "usable"}]。ログにも出す。

    usable は、今のトポロジーが保存したときと同じか (違えばツールでは使われずに残っている)。
    """
    rows = []
    for mesh in guide_attribute.meshes_with_guides():
        try:
            guide_set, saved_topology = guide_json.loads(guide_attribute.read_text(mesh) or "")
        except ValueError:
            rows.append({"mesh": mesh, "guides": 0, "usable": False})
            log.info("{}: 読めないガイドのデータ".format(mesh.fullPath()))
            continue

        usable = saved_topology == topology_of(len(mesh.points()), mesh.edgeVertices())
        rows.append({"mesh": mesh, "guides": len(guide_set.guides), "usable": usable})
        log.info("{}: ガイド {} 本{}".format(mesh.fullPath(), len(guide_set.guides),
                                          "" if usable else " (トポロジーが違うので使われていません)"))

    if not rows:
        log.info("ガイドを保存しているメッシュはありません")

    return rows


def delete_all_guides(confirm=True):
    """シーンに保存したガイドをすべて消す。confirm なら (GUI のとき) 確認する。消したメッシュの数を返す。"""
    meshes = guide_attribute.meshes_with_guides()
    if not meshes:
        log.info("ガイドを保存しているメッシュはありません")
        return 0

    message = "{} 個のメッシュに保存したガイドをすべて削除しますか？ (Ctrl+Z で戻せます)".format(len(meshes))
    if confirm and not _confirmed(message):
        return 0

    return delete_guides(meshes)


def delete_target_guides(targets):
    """ツールの対象のメッシュ (TargetMesh) のガイドをすべて消す (作成中のガイドも。1 回の Undo)。消した本数を返す。

    パネルの「全削除」。Ctrl+Z で戻せるので確認しない (ユーザーの指定)。ガイドの組を空にするだけなので、guide_edit を
    通る (ほかのガイドの編集と同じく、Ctrl+Z で組とアトリビュートの両方が戻る)。
    """
    items = [(target, GuideSet()) for target in targets if target.guideSet().guides]
    count = sum(len(target.guideSet().guides) for target, _ in items)
    if not items:
        log.info("消すガイドがありません")
        return 0

    guide_edit.apply_many(items)
    log.info("ガイドを {} 本消しました (Ctrl+Z で戻せます)".format(count))

    return count


def delete_guides(meshes):
    """meshes (utils.mesh.Mesh) に保存したガイドを消す (1 回の Undo)。消したメッシュの数を返す。

    ツールの中の写し (guide_store) も空にする。Ctrl+Z でアトリビュートと写しの両方を元に戻す。
    """
    store = guide_store.store()
    items = []
    for mesh in meshes:
        text = guide_attribute.read_text(mesh)
        if text is not None:
            items.append((mesh, text, store.guideSet(mesh.key())))

    if not items:
        log.warning("ガイドを保存しているメッシュがありません")
        return 0

    deleted = []

    def redo():
        deleted[:] = []
        for mesh, _, _ in items:
            try:
                guide_attribute.delete(mesh)
            except RuntimeError as error:
                log.warning("{}: ガイドを消せません ({})".format(mesh.fullPath(), error))
                continue

            store.setGuideSet(mesh.key(), GuideSet())
            deleted.append(mesh)

    def restore():
        for mesh, text, before in items:
            if mesh in deleted:
                guide_attribute.write_text(mesh, text)
                store.setGuideSet(mesh.key(), before)

    undo.run(redo, restore)
    log.info("{} 個のメッシュのガイドを消しました".format(len(deleted)))

    return len(deleted)


def _confirmed(message):
    # 確認のダイアログで「削除」を押したか (batch では聞かずに True)
    if cmds.about(batch=True):
        return True

    answer = cmds.confirmDialog(title="UVSeamTool", message=message, button=["削除", "キャンセル"],
                                defaultButton="キャンセル", cancelButton="キャンセル", dismissString="キャンセル")

    return answer == "削除"
