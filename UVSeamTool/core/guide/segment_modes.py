"""
区間を求め直す・点を消す (版 1 は最短の区間だけ)。

surface はメッシュの表面 (tool.target_mesh.TargetMesh が持つ graph() = MeshGraph)。点のドラッグ・切り離しと接続・
まとめて動かす・点の削除が、点を変えたあとの区間をここで求め直す。
"""

from __future__ import annotations

from dataclasses import replace

from ..path.shortest_path import shortest_path
from .guide_segment import GuideSegment, SHORTEST


def solve_segment(guide, index, surface):
    """guide の index 番目の区間を最短パスで求めた GuideSegment (点は変えない)。つながらなければ None。"""
    count = len(guide.points)
    seam  = shortest_path(surface.graph(), guide.points[index].vertex, guide.points[(index + 1) % count].vertex)

    return None if seam is None else GuideSegment(mode=SHORTEST, seam=tuple(seam))


def moved_segments(guide, point_indices):
    """点 (番号の集合) を動かした・足したときに、求め直す区間の番号の集合 (その点を端に持つ区間)。"""
    count  = len(guide.points)
    points = set(point_indices)

    return {index for index in range(len(guide.segments)) if {index, (index + 1) % count} & points}


def resolve(guide, indices, surface):
    """indices の区間を求め直したガイド。求められなければ None。"""
    segments = list(guide.segments)
    for index in sorted(indices):
        segment = solve_segment(guide, index, surface)
        if segment is None:
            return None
        segments[index] = segment

    return replace(guide, segments=tuple(segments))


def delete_point(guide, index, surface):
    """index 番目の点を消したガイド。点が 1 つしか残らない・つなげなければ None。

    途中の点を消したら、前後の点を最短パスでつなぐ。開いたガイドの端の点を消したら、その区間を落とす。
    """
    count  = len(guide.points)
    if count <= 2:
        return None

    if not guide.closed and index in (0, count - 1):
        if index == 0:
            return replace(guide, points=guide.points[1:], segments=guide.segments[1:])
        return replace(guide, points=guide.points[:-1], segments=guide.segments[:-1])

    before = (index - 1) % count
    points = guide.points[:index] + guide.points[index + 1:]
    if index == 0:
        # 閉じたガイドの最初の点: 点の列は 1 つ目から始まり、最後の区間が最後の点 -> 新しい最初の点 になる
        segments = guide.segments[1:count - 1] + (guide.segments[before],)
        joined   = len(segments) - 1
    else:
        segments = guide.segments[:index - 1] + (guide.segments[before],) + guide.segments[index + 1:]
        joined   = index - 1

    return resolve(replace(guide, points=points, segments=segments), {joined}, surface)
