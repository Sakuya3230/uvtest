"""
対称の相手のガイド (鏡に写す・変更に合わせて作り直す)。Maya には触らない。
"""

from __future__ import annotations

from dataclasses import replace

from ..guide.guide_point import vertex_point
from ..guide.set_editing import find_guide


def sync_partners(before, after, vertex_of):
    """ガイドの組の変更 (before -> after) に合わせて、相手のガイドを作り直した組と、写せなかったガイドの数を返す。

    vertex_of(頂点) は反対側の頂点 (見つからなければ -1)。core.symmetry.mirror_map.MirrorMap.vertex。
      増えた・形が変わったガイド -> 鏡に写して相手を作る / 作り直す (相手の id はそのまま)。相手のほうを編集すれば元を作り直す
      消えたガイド               -> 相手も消す
      対称の面の上のガイド (写しても自分と同じ) には相手を作らない
      反対側が見つからない頂点を通るガイドは、相手を作らない / 作り直さない (数えて返す)
    点とシーム (頂点の列) は vertex_of で写す。鏡に写したエッジの道は、そのまま反対側のエッジの道になる。
    """
    result   = after
    handled  = set()   # 今回作り直した相手 (相手の変更として、また作り直さない)
    failed   = 0

    for guide in before.guides:
        partner = find_guide(after, guide.partner) if guide.partner is not None else None
        if find_guide(after, guide.id) is None and partner is not None and partner.partner == guide.id:
            result = _remove(result, guide.partner)   # 相手がまだこちらを指していれば (つないで相手を外したガイドは残す)

    for guide in after.guides:
        if guide.id in handled or find_guide(before, guide.id) == guide:
            continue

        current = find_guide(result, guide.id)
        if current is None:
            continue

        result, partner_id, ok = _sync_one(result, current, vertex_of)
        failed += 0 if ok else 1
        if partner_id is not None:
            handled.add(partner_id)

    return result, failed


def with_partners(guide_set, guides):
    """guides と、その相手のガイド (組の中にあれば。重なりなし)。対称のカット / 縫合の対象を決めるのに使う。"""
    result = list(guides)
    ids    = {guide.id for guide in guides}
    for guide in guides:
        partner = find_guide(guide_set, guide.partner) if guide.partner is not None else None
        if partner is not None and partner.id not in ids:
            result.append(partner)
            ids.add(partner.id)

    return result


def _sync_one(guide_set, guide, vertex_of):
    # guide の相手を作る / 作り直す。(新しい組, 相手の id か None, 写せたか)
    mirrored = _mirror(guide, vertex_of)
    if mirrored is None:
        return guide_set, guide.partner, False

    points, segments = mirrored
    if _same_path(guide.points, guide.segments, points, segments, guide.closed):
        return _unlink(guide_set, guide), None, True   # 対称の面の上 (写しても自分と同じ)。相手は作らない (前の相手は消す)

    existing   = find_guide(guide_set, guide.partner) if guide.partner is not None else None
    partner_id = existing.id if existing is not None else max(g.id for g in guide_set.guides) + 1
    partner    = replace(guide, id=partner_id, points=points, segments=segments, partner=guide.id)
    linked     = replace(guide, partner=partner_id)

    guides = tuple(linked if g.id == guide.id else partner if g.id == partner_id else g for g in guide_set.guides)
    if existing is None:
        guides += (partner,)

    return replace(guide_set, guides=guides), partner_id, True


def _mirror(guide, vertex_of):
    # ガイドの点・シームを鏡に写した (点, 区間)。反対側が見つからない頂点があれば None
    vertices = [point.vertex for point in guide.points] + [v for segment in guide.segments for v in segment.seam]
    if any(vertex_of(v) < 0 for v in vertices):
        return None

    points   = tuple(vertex_point(vertex_of(point.vertex)) for point in guide.points)
    segments = tuple(replace(segment, seam=tuple(vertex_of(v) for v in segment.seam)) for segment in guide.segments)

    return points, segments


def _same_path(points, segments, other_points, other_segments, closed=False):
    # 写したものが自分と同じ線か (対称の面の上。向きが逆でも同じ)。区間があればシームの頂点、無ければ点で比べる。
    # 閉じたガイド (面をまたぐリングなど) は、写すと輪の始まりがずれるので、通る頂点の集まりで比べる
    if segments:
        mine   = [v for segment in segments for v in segment.seam]
        theirs = [v for segment in other_segments for v in segment.seam]
    else:
        mine, theirs = list(points), list(other_points)

    if closed and segments:
        return set(theirs) == set(mine)

    return theirs == mine or theirs == mine[::-1]


def _unlink(guide_set, guide):
    # guide の相手を消して、guide の相手の id を外す
    if guide.partner is None:
        return guide_set

    guide_set = _remove(guide_set, guide.partner)
    guides    = tuple(replace(g, partner=None) if g.id == guide.id else g for g in guide_set.guides)

    return replace(guide_set, guides=guides)


def _remove(guide_set, guide_id):
    # id のガイドを消す (作成中なら作成中でなくなる)
    guides    = tuple(guide for guide in guide_set.guides if guide.id != guide_id)
    active_id = None if guide_set.active_id == guide_id else guide_set.active_id

    return replace(guide_set, guides=guides, active_id=active_id)
