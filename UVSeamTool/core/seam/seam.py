"""
ガイド -> シーム (エッジの番号の列)。
"""

from __future__ import annotations


def seam_edges(guide, graph):
    """ガイドの区間が通るエッジの番号 (通る順・重なりなし) の tuple。"""
    edges = []
    seen  = set()

    # 区間の頂点の隣どうしをエッジにする (区間の境目のエッジは前後で重なるので 1 回だけ)
    for segment in guide.segments:
        for a, b in zip(segment.seam, segment.seam[1:]):
            edge = graph.edgeBetween(a, b)
            if edge is not None and edge not in seen:
                seen.add(edge)
                edges.append(edge)

    return tuple(edges)
