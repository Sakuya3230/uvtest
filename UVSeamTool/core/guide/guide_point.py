"""
ガイドの点 (頂点の点)。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuidePoint:
    """ガイドの点 1 つ (変えられない値)。頂点の番号を持つ。作るときは vertex_point で。

    位置そのものは持たない (メッシュの頂点の位置。変形に付いて行く)。保存するときだけ控えの位置を書く。
    版 2 (UVSeamTool2) は表面の点・ほかのガイドに乗る点も持つ。版 1 は最短の区間だけなので頂点の点だけ。
    """

    vertex      : int       # 頂点の番号


def vertex_point(vertex):
    """頂点の点。"""
    return GuidePoint(vertex=int(vertex))
