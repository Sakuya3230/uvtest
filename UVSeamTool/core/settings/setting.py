"""
設定の項目 1 つの定義。
"""

from __future__ import annotations

from dataclasses import dataclass

COLOR   = "color"    # (r, g, b)。それぞれ 0〜1
BOOL    = "bool"     # オン / オフ
CHOICE  = "choice"   # choices の値のどれか
FLOAT   = "float"    # minimum〜maximum の数


@dataclass(frozen=True)
class Setting:
    """設定の項目 1 つの定義 (変えられない値)。表 (core.settings.definitions) に並べる。

    保存・ツール設定のウィンドウは、この表から作る。項目を足すときは表に 1 行足す。
    """

    key         : str               # 保存とプログラムで使う名前
    kind        : str               # 値の種類 (COLOR / BOOL / CHOICE / FLOAT)
    default     : object            # 既定の値
    label       : str               # ツール設定のウィンドウに出す名前
    category    : str               # ツール設定のウィンドウの欄
    choices     : tuple = ()        # CHOICE の (値, 表示名) の列
    minimum     : float = None      # FLOAT の範囲 (外は端に寄せる)
    maximum     : float = None
