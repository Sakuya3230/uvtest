# -*- coding: utf-8 -*-
"""
設定を Maya の設定 (optionVar) に保存する。

    storage = OptionVarStorage()           # optionVar "uvPathCutSettings"
    settings = Settings(storage)           # 作ったときに読み、変えるたびに保存する

optionVar は Maya を閉じるときに userPrefs.mel に書かれ、次に起動したときも残る。
値は JSON の文字列 1 つにまとめる (設定を足しても optionVar を増やさずに済む)。
既定値と同じ項目は書かない (既定値を変えたら、保存していない項目は新しい既定値になる)。
"""
import json

import maya.cmds as cmds

from ..core import settings as settings_module

__all__ = ["OPTION_VAR", "OptionVarStorage"]

OPTION_VAR = "uvPathCutSettings"


class OptionVarStorage(object):
    """Settings の保存先 (load / save) を optionVar で持つ。"""

    def __init__(self, name=OPTION_VAR):
        self.name = name

    def load(self):
        """保存した dict。無い・読めなければ None (Settings が既定値にする)。"""
        try:
            if not cmds.optionVar(exists=self.name):
                return None
            data = json.loads(cmds.optionVar(query=self.name))
        except (RuntimeError, ValueError, TypeError):
            return None
        return data if isinstance(data, dict) else None

    def save(self, values):
        """既定値と違う項目だけを JSON で保存する。全部が既定値なら optionVar を消す。"""
        defaults = settings_module.defaults()
        changed = {key: value for key, value in values.items() if defaults.get(key) != value}
        if changed:
            cmds.optionVar(stringValue=(self.name, json.dumps(changed, sort_keys=True)))
        else:
            self.remove()

    def remove(self):
        if cmds.optionVar(exists=self.name):
            cmds.optionVar(remove=self.name)
