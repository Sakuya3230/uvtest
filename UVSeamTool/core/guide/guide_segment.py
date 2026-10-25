"""
ガイドの区間 (点と点の間)。
"""

from __future__ import annotations

from dataclasses import dataclass

SHORTEST    = "shortest"    # エッジの最短パス (まっすぐさも)。版 1 の区間の作り方はこれだけ


@dataclass(frozen=True)
class GuideSegment:
    """隣り合う 2 つの点の間の区間 (変えられない値)。作り方とシームを持つ。

    シーム (seam) は求めたエッジの道 (頂点の列。両端の点の頂点を含む) で、保存してこれを正とする。求め直すのは、
    その区間の端の点を変えたときだけ (設定を変えても、今あるガイドの切れ方は変わらない)。
    """

    mode        : str   = SHORTEST  # 作り方 (保存の形を版 2 と揃えるために持つ)
    seam        : tuple = ()        # 求めたエッジの道 (頂点の番号の列)
