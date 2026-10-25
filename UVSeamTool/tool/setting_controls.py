"""
ツール設定のウィンドウの、設定の種類ごとの部品 (作る・コマンドを付ける・値を入れる・読む)。
"""

import maya.cmds as cmds

from ..core.settings.setting import BOOL, CHOICE, COLOR, FLOAT

LABEL_WIDTH     = 130   # 部品の左のラベルの幅 (ボタンの行のラベルと揃える)
MAX_RADIO       = 4     # radioButtonGrp が作れるボタンの数。これより選択肢が多ければドロップダウン (optionMenuGrp)


def make(setting):
    """設定の項目の部品を作り、フルパスを返す (コマンドは attach で付ける)。"""
    if setting.kind == COLOR:
        return cmds.colorSliderGrp(label=setting.label, columnWidth3=(LABEL_WIDTH, 50, 140))

    if setting.kind == BOOL:
        return cmds.checkBoxGrp(label=setting.label, numberOfCheckBoxes=1, label1="", columnWidth=(1, LABEL_WIDTH))

    if setting.kind == CHOICE and _uses_menu(setting):
        path = cmds.optionMenuGrp(label=setting.label, columnWidth=(1, LABEL_WIDTH))
        for _, label in setting.choices:
            cmds.menuItem(label=label)   # 今のドロップダウンに足される
        return path

    if setting.kind == CHOICE:
        count  = len(setting.choices)
        labels = {"labelArray{}".format(count): [label for _, label in setting.choices]}
        return cmds.radioButtonGrp(label=setting.label, numberOfRadioButtons=count, columnWidth=(1, LABEL_WIDTH),
                                   **labels)

    if setting.kind == FLOAT:
        return cmds.floatSliderGrp(label=setting.label, field=True, precision=4, minValue=setting.minimum,
                                   maxValue=setting.maximum, fieldMinValue=setting.minimum,
                                   fieldMaxValue=setting.maximum, columnWidth=(1, LABEL_WIDTH))

    raise ValueError(setting.kind)


def attach(path, setting, command):
    """部品を変えたら command() を呼ぶようにする。"""
    if setting.kind == COLOR:
        cmds.colorSliderGrp(path, edit=True, changeCommand=command)
    elif setting.kind == BOOL:
        cmds.checkBoxGrp(path, edit=True, changeCommand1=command)
    elif setting.kind == CHOICE and _uses_menu(setting):
        cmds.optionMenuGrp(path, edit=True, changeCommand=command)
    elif setting.kind == CHOICE:
        for index in range(len(setting.choices)):
            cmds.radioButtonGrp(path, edit=True, **{"onCommand{}".format(index + 1): command})
    elif setting.kind == FLOAT:
        cmds.floatSliderGrp(path, edit=True, changeCommand=command)


def show(path, setting, value):
    """部品に値を入れる (-edit では changeCommand は呼ばれない)。"""
    if setting.kind == COLOR:
        cmds.colorSliderGrp(path, edit=True, rgb=value)
    elif setting.kind == BOOL:
        cmds.checkBoxGrp(path, edit=True, value1=bool(value))
    elif setting.kind == CHOICE:
        values = [choice for choice, _ in setting.choices]
        _choice_command(setting)(path, edit=True, select=values.index(value) + 1)
    elif setting.kind == FLOAT:
        cmds.floatSliderGrp(path, edit=True, value=float(value))


def read(path, setting):
    """部品の今の値。"""
    if setting.kind == COLOR:
        return cmds.colorSliderGrp(path, query=True, rgb=True)

    if setting.kind == BOOL:
        return cmds.checkBoxGrp(path, query=True, value1=True)

    if setting.kind == CHOICE:
        return setting.choices[_choice_command(setting)(path, query=True, select=True) - 1][0]

    return cmds.floatSliderGrp(path, query=True, value=True)


def set_enabled(path, setting, enabled):
    """部品を使える / 灰色にする。"""
    command = {COLOR: cmds.colorSliderGrp, BOOL: cmds.checkBoxGrp, CHOICE: _choice_command(setting),
               FLOAT: cmds.floatSliderGrp}[setting.kind]
    command(path, edit=True, enable=enabled)


def _uses_menu(setting):
    # 選択肢が多くてラジオボタンにできないか
    return len(setting.choices) > MAX_RADIO


def _choice_command(setting):
    # 選択肢の部品のコマンド (ドロップダウンかラジオボタン。どちらも select で番号 (1 から) を読み書きできる)
    return cmds.optionMenuGrp if _uses_menu(setting) else cmds.radioButtonGrp
