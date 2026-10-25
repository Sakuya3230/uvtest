"""
ガイドの切り離し (選んだ点で分ける) と接続 (2 本の端どうしをつなぐ・1 本を閉じる) (docs/27_shortest_only.md)。

    split_guide(組, ガイドの id, 点の番号の集合)              選んだ点で切り離した組
    join_guides(組, id, もう 1 本の id か None, 表面, ends)   つないだ組 (None なら閉じる。ends で端を指定できる)
対称の相手は guide_edit が作り直す。
"""

from __future__ import annotations

from dataclasses import replace

from ...compat.accel import np
from . import segment_modes
from .guide_segment import GuideSegment
from .set_editing import find_guide, next_guide_id


def split_guide(guide_set, guide_id, point_indices):
    """guide_id のガイドを、点 point_indices で切り離した組。切れなければ None。

    開いた線: 端でない選んだ点それぞれで切る (選んだ点は両側の線の端になる)。最初の線が元の id を使う。
    閉じた線: 選んだ点のうち最初の点で開き、残りの点で切る。
    """
    guide = find_guide(guide_set, guide_id)
    if guide is None or not guide.segments:
        return None

    count   = len(guide.points)
    indices = sorted({int(i) for i in point_indices if 0 <= int(i) < count})
    if guide.closed:
        if not indices:
            return None
        start   = indices[0]
        order   = list(range(start, count)) + list(range(start))
        guide   = replace(guide, points=tuple(guide.points[k] for k in order) + (guide.points[start],),
                          segments=tuple(guide.segments[k] for k in order), closed=False)
        indices = [(i - start) % count for i in indices[1:]]
    elif not any(0 < i < count - 1 for i in indices):
        return None

    cuts   = [0] + [i for i in indices if 0 < i < len(guide.points) - 1] + [len(guide.points) - 1]
    pieces = [replace(guide, points=guide.points[a:b + 1], segments=guide.segments[a:b]) for a, b in zip(cuts, cuts[1:])]
    result = replace(guide_set, guides=tuple(pieces[0] if g.id == guide_id else g for g in guide_set.guides))
    for piece in pieces[1:]:
        result = replace(result, guides=result.guides + (replace(piece, id=next_guide_id(result), partner=None),))

    return result


def join_guides(guide_set, first_id, second_id, surface, ends=None):
    """2 本の開いた線の端どうしをつないだ組 (second_id が None か同じなら、first_id の始めと終わりをつないで閉じる)。

    ends は {ガイドの id: つなぐ端 (0 = 始め / 1 = 終わり)}。端を指定したガイドはその端、指定しないガイドは、4 通りの
    端の組のうち (指定した端と組める中で) いちばん近い端。端が同じ頂点なら点を 1 つにまとめ、そうでなければ最短の
    区間を足す。つないだガイドは first_id。つなげなければ None。
    """
    first  = find_guide(guide_set, first_id)
    second = find_guide(guide_set, second_id) if second_id not in (None, first_id) else None
    if first is None or first.closed or not first.segments:
        return None

    if second_id not in (None, first_id):
        if second is None or second.closed or not second.segments:
            return None
        joined  = _join_two(first, second, surface, ends or {})
        removed = {second.id}
    else:
        joined  = _close(first, surface)
        removed = set()
    if joined is None:
        return None

    if second is not None and first.partner == second.id:
        joined = replace(joined, partner=None)   # 互いの相手どうし: つないだ線は中心をまたぐので相手を作らない
    guides = tuple(joined if g.id == first.id else g for g in guide_set.guides if g.id not in removed)

    return replace(guide_set, guides=guides)


def _join_two(first, second, surface, ends):
    # first の終わりに second の始めが来るよう向きを揃えてつなぐ (指定した端、無ければ近い端の組を選ぶ)
    positions = surface.graph().positions()[[first.points[0].vertex, first.points[-1].vertex,
                                             second.points[0].vertex, second.points[-1].vertex]]
    heads     = (ends[first.id],) if first.id in ends else (0, 1)          # first の端 (0 = 始め, 1 = 終わり)
    tails     = (ends[second.id] + 2,) if second.id in ends else (2, 3)    # second の端 (2 = 始め, 3 = 終わり)
    pairs     = [(np.linalg.norm(positions[a] - positions[b]), a, b) for a in heads for b in tails]
    _, a, b   = min(pairs)
    head      = _reversed(first) if a == 0 else first
    tail      = _reversed(second) if b == 3 else second
    work      = replace(head, points=head.points + tail.points, segments=head.segments + (None,) + tail.segments)

    return _fill_joint(work, len(head.segments), surface)


def _close(guide, surface):
    # 始めと終わりをつないで閉じる (3 点以上)
    if len(guide.points) < 3:
        return None

    return _fill_joint(replace(guide, segments=guide.segments + (None,), closed=True), len(guide.segments), surface)


def _fill_joint(work, joint, surface):
    # 区間 joint (None の所) を作る。両端が同じ頂点なら点をまとめる (閉じたガイドは最後の点を、2 本なら後ろの最初の点を消す)
    end = (joint + 1) % len(work.points)
    if work.points[joint].vertex == work.points[end].vertex:
        points   = work.points[:joint + 1] + work.points[joint + 2:] if end else work.points[:-1]
        segments = work.segments[:joint] + work.segments[joint + 1:]
        merged   = replace(work, points=points, segments=segments)
        return None if merged.closed and len(merged.points) < 3 else merged   # 区間はもうつながっている

    work = replace(work, segments=tuple(GuideSegment() if s is None else s for s in work.segments))

    return segment_modes.resolve(work, {joint}, surface)


def _reversed(guide):
    # 向きを逆にしたガイド (点・区間・シームを逆に)
    segments = tuple(replace(s, seam=tuple(reversed(s.seam))) for s in reversed(guide.segments))

    return replace(guide, points=tuple(reversed(guide.points)), segments=segments)
