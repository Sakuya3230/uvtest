"""
ガイドの組の編集。どの関数も元の組は変えず、新しい組を返す。何も変わらないときは None を返す。
"""

from __future__ import annotations

from dataclasses import replace

from . import editing, segment_modes
from .guide import Guide
from .guide_point import GuidePoint, vertex_point


def active_guide(guide_set):
    """作成中のガイド (無ければ None)。"""
    return find_guide(guide_set, guide_set.active_id)


def find_guide(guide_set, guide_id):
    """id のガイド (無ければ None)。"""
    for guide in guide_set.guides:
        if guide.id == guide_id:
            return guide

    return None


def add_point(guide_set, graph, vertex):
    """作成中のガイドの端に点を足す。作成中のガイドが無ければ、その頂点から新しいガイドを始める。

    最後の点と同じ頂点・つながっていない頂点なら None。
    """
    active = active_guide(guide_set)
    if active is None:
        return _start_guide(guide_set, vertex)

    if active.points[-1].vertex == vertex:
        return None

    guide = editing.add_point(active, graph, vertex)
    if guide is None:
        return None

    return _replace_guide(guide_set, guide)


def remove_last_point(guide_set):
    """作成中のガイドの最後の点を消す。点が 1 つだけなら、ガイドごと捨てる。"""
    active = active_guide(guide_set)
    if active is None:
        return None

    if len(active.points) == 1:
        return discard_active(guide_set)

    return _replace_guide(guide_set, editing.remove_last_point(active))


def finish_active(guide_set):
    """作成中のガイドを確定する (作成中でなくなる)。点が 1 つだけなら、区間が無いので捨てる。"""
    active = active_guide(guide_set)
    if active is None:
        return None

    if len(active.points) == 1:
        return discard_active(guide_set)

    return replace(guide_set, active_id=None)


def discard_active(guide_set):
    """作成中のガイドを捨てる。"""
    if active_guide(guide_set) is None:
        return None

    guides = tuple(guide for guide in guide_set.guides if guide.id != guide_set.active_id)

    return replace(guide_set, guides=guides, active_id=None)


def replace_guide(guide_set, guide):
    """同じ id のガイドを guide に替える。変わらなければ None。"""
    if find_guide(guide_set, guide.id) == guide:
        return None

    return _replace_guide(guide_set, guide)


def remove_guides(guide_set, guide_ids):
    """id のガイドを消す (作成中のガイドを消したら、作成中でなくなる)。1 本も無ければ None。"""
    guides = tuple(guide for guide in guide_set.guides if guide.id not in guide_ids)
    if len(guides) == len(guide_set.guides):
        return None

    active_id = None if guide_set.active_id in guide_ids else guide_set.active_id

    return replace(guide_set, guides=guides, active_id=active_id)


def delete_points(guide_set, surface, points):
    """点 (ガイドの id, 点の番号) の集合を消す。点が 1 つしか残らないガイドは、ガイドごと消す。何も変わらなければ None。

    同じガイドの点は、番号の大きい方から消す (先に消した点で、残りの番号がずれないように)。前後の点は最短パスで
    つなぐ (segment_modes.delete_point。surface は表面 = TargetMesh)。
    """
    new_set = guide_set
    for guide_id in sorted({guide_id for guide_id, _ in points}):
        guide = find_guide(new_set, guide_id)
        if guide is None:
            continue

        for index in sorted((i for g, i in points if g == guide_id), reverse=True):
            guide = segment_modes.delete_point(guide, index, surface) if guide is not None else None

        if guide is None:
            new_set = remove_guides(new_set, {guide_id}) or new_set
        else:
            new_set = _replace_guide(new_set, guide)

    return None if new_set == guide_set else new_set


def next_guide_id(guide_set):
    """新しいガイドに付ける id (今のいちばん大きい id + 1)。"""
    return max((guide.id for guide in guide_set.guides), default=-1) + 1


def add_guide(guide_set, guide):
    """できあがったガイドを足した組 (作成中にはしない。id は next_guide_id で付けたもの)。"""
    return replace(guide_set, guides=guide_set.guides + (guide,))


def _start_guide(guide_set, start):
    # start (頂点の番号か GuidePoint) から新しいガイドを始めた組
    guide_id = max((guide.id for guide in guide_set.guides), default=-1) + 1
    point    = start if isinstance(start, GuidePoint) else vertex_point(start)
    guide    = Guide(id=guide_id, points=(point,))

    return replace(guide_set, guides=guide_set.guides + (guide,), active_id=guide_id)


def _replace_guide(guide_set, new_guide):
    guides = tuple(new_guide if guide.id == new_guide.id else guide for guide in guide_set.guides)

    return replace(guide_set, guides=guides)
