"""
1 本のガイド (点の列 + 点の間の区間)。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Guide:
    """1 本のガイド (変えられない値)。点の列と、点の間ごとの区間を持つ。編集は core.guide.editing の関数で。"""

    id          : int
    points      : tuple         = ()        # GuidePoint の列
    segments    : tuple         = ()        # GuideSegment の列。開いた線は len(points) - 1 本、閉じた線は len(points) 本
    closed      : bool          = False     # 閉じたガイド (最後の点 -> 最初の点の区間がある)
    partner     : Optional[int] = None      # 対称の相手のガイドの id (同じメッシュの中。core.symmetry.guide_mirror)
