"""
設定を JSON のファイルに読み書きする (Maya の版をまたいで同じファイルを使う)。
"""

from __future__ import annotations

import json
import os

FORMAT  = "UVSeamTool.settings"
VERSION = 1


class JsonStorage:
    """設定の値 ({キー: 値}) を 1 つの JSON のファイルに持つ。

    書くときは同じフォルダの一時ファイルに書いてから入れ替える (書いている途中で落ちても壊れない)。
    読めないファイルは空として扱う (設定は既定の値になる)。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, path):
        self._path = path

    # -- 公開メソッド ---------------------------------------------------------
    def path(self):
        return self._path

    def load(self):
        """保存した値の dict。ファイルが無い・読めなければ空の dict。"""
        try:
            with open(self._path, "r", encoding="utf-8") as stream:
                data = json.load(stream)
        except (OSError, ValueError):
            return {}

        if not isinstance(data, dict) or data.get("format") != FORMAT:
            return {}

        values = data.get("values")

        return values if isinstance(values, dict) else {}

    def save(self, values):
        """値の dict を書く。"""
        folder = os.path.dirname(self._path)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder)

        data      = {"format": FORMAT, "version": VERSION, "values": values}
        temporary = self._path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, sort_keys=True)

        os.replace(temporary, self._path)
