"""
メッシュ 1 つのガイドの組。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GuideSet:
    """メッシュ 1 つのガイドの組 (変えられない値)。編集は core.guide.set_editing の関数で。

    作成中のガイドも guides に入っていて、その番号を active_id で指す。Undo はこの値の前と後を入れ替えるだけ。
    """

    guides      : tuple         = ()    # Guide の列 (作った順)
    active_id   : Optional[int] = None  # 作成中のガイドの id (作成中でなければ None)
