"""
編集のモードで選んだもの (ガイド・点) への操作 (削除・カット / 縫合・切り離し・接続)。

選んだものは EditTool が持ち、ここへ渡す: selected = ガイドの ref (メッシュの鍵, ガイドの id) の集合、
selected_points = (ref, 点の番号) の集合。どの操作も、メッシュにまたがっても 1 回の Undo。
"""

from ..core.guide import set_editing, split_join
from ..utils import log
from . import guide_edit, uv_apply


def delete_selection(targets, selected, selected_points):
    """選んでいる点を消す (点を選んでいなければ、選んでいるガイドを消す)。"""
    if selected_points:
        items = []
        for target in targets:
            points  = {(ref[1], index) for ref, index in selected_points if ref[0] == target.key()}
            new_set = set_editing.delete_points(target.guideSet(), target, points) if points else None
            if new_set is not None:
                items.append((target, new_set))
        if items:
            guide_edit.apply_many(items)
            log.info("点を {} つ消しました".format(len(selected_points)))
        return

    items = []
    for target in targets:
        guide_ids = {guide_id for key, guide_id in selected if key == target.key()}
        new_set   = set_editing.remove_guides(target.guideSet(), guide_ids) if guide_ids else None
        if new_set is not None:
            items.append((target, new_set))
    if items:
        guide_edit.apply_many(items)
        log.info("ガイドを {} 本消しました".format(len(selected)))


def apply_to_selection(targets, selected, operation):
    """選んでいるガイドに、カット / 縫合 (tool.uv_apply.CUT / SEW) を当てる。"""
    items = [(target, [guide for guide in target.guideSet().guides if (target.key(), guide.id) in selected])
             for target in targets]
    if not any(guides for _, guides in items):
        log.warning("ガイドを選んでください")
        return

    uv_apply.apply_targets(items, operation)


def split_selection(targets, selected_points):
    """選んだ点でガイドを切り離す (開いた線は分け、閉じた線は開く)。"""
    items = []
    for target in targets:
        guide_set = target.guideSet()
        for guide_id in sorted({ref[1] for ref, _ in selected_points if ref[0] == target.key()}):
            points    = {index for ref, index in selected_points if ref == (target.key(), guide_id)}
            guide_set = split_join.split_guide(guide_set, guide_id, points) or guide_set
        if guide_set is not target.guideSet():
            items.append((target, guide_set))

    if items:
        guide_edit.apply_many(items)
        log.info("ガイドを切り離しました")
    else:
        log.warning("切り離す点を選んでください (開いたガイドは端でない点、閉じたガイドはどの点でも)")


def join_selection(targets, selected, selected_points=()):
    """選んだ 2 本のガイドの端どうしをつなぐ (1 本だけなら、その始めと終わりをつないで閉じる)。

    端の点を選んでいれば、そのガイドはその端でつなぐ (選んでいなければ近いほうの端)。
    """
    if len(selected) not in (1, 2) or len({key for key, _ in selected}) != 1:
        log.warning("接続するガイドを、同じメッシュで 1 本 (閉じる) か 2 本選んでください")
        return

    refs    = sorted(selected)
    target  = targets.find(refs[0][0])
    ends    = {}
    for ref, index in selected_points:
        guide = set_editing.find_guide(target.guideSet(), ref[1]) if ref in refs else None
        if guide is not None and not guide.closed and index in (0, len(guide.points) - 1):
            ends[guide.id] = 0 if index == 0 else 1
    new_set = split_join.join_guides(target.guideSet(), refs[0][1], refs[1][1] if len(refs) == 2 else None, target, ends)
    if new_set is None:
        log.warning("接続できません (閉じたガイド・点が足りない・つながらない)")
        return

    guide_edit.apply(target, new_set)
    log.info("ガイドを{}しました".format("接続" if len(refs) == 2 else "閉じて接続"))
