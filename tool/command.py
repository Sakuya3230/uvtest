# -*- coding: utf-8 -*-
"""
コンテキストのコマンド (uvPathCutCtx)・ツールのコマンド (uvPathCutTool)・コンテキストの削除。

    cmds.uvPathCutCtx("名前")                          コンテキストを作る (makeObj)
    cmds.uvPathCutCtx("名前", edit=True, pickMode="vertex")
    cmds.uvPathCutCtx("名前", query=True, pickMode=True)
    delete_tool_context()                              リロードの前に消す

フラグは設定の定義表 (core/settings.DEFINITIONS) から作る (段階 1)。定義表に無いフラグ (リセット・
まとめて実行・クリア・操作・色) はこのモジュールの *_FLAG。プラグインは tool/context.py から
これらの名前を引く (context が再び公開する)。
"""
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui
import maya.cmds as cmds

from .. import log
from ..constants import CONTEXT_COMMAND, TOOL_CONTEXT
from ..core import settings as settings_module
from ..core.actions import action_by_id
from ..core.settings import BOOL, CHOICE, COLOR, FLOAT, DEFINITIONS, SettingsError, keys_in_section

__all__ = ["UVPathCutContextCommand", "ToolCommand", "delete_tool_context", "RESET_FLAG",
           "APPLY_FLAG", "CLEAR_FLAG", "RUN_ACTION_FLAG", "SET_COLOR_FLAG", "RESET_COLORS_FLAG"]

# 設定の定義表に無いフラグ (編集だけ)
RESET_FLAG = ("-rs", "-resetSettings")   # 真偽値: True ならすべて既定値に戻す
APPLY_FLAG = ("-ap", "-apply")           # 文字列 (cut / sew): ためた区間をまとめて実行する (段階 9)
CLEAR_FLAG = ("-cl", "-clear")           # 真偽値: True なら区間・スタート・選択をすべて外す (段階 10)
RUN_ACTION_FLAG = ("-ra", "-runAction")  # 文字列: 操作の表の ID の操作を行う (段階 12)
SET_COLOR_FLAG = ("-sc", "-setColor")    # 文字列 "キー r g b": 色の設定を変える
RESET_COLORS_FLAG = ("-rcl", "-resetColors")   # 真偽値: True なら色の設定だけを既定に戻す

# 設定の種類 -> フラグの引数の型
_FLAG_TYPES = {BOOL: om.MSyntax.kBoolean, CHOICE: om.MSyntax.kString, FLOAT: om.MSyntax.kDouble}


class UVPathCutContextCommand(omui.MPxContextCommand):
    """uvPathCutCtx コマンド。フラグは設定の定義表 (DEFINITIONS) から作る。

    作成:       cmds.uvPathCutCtx("名前")
    編集:       cmds.uvPathCutCtx("名前", edit=True, pickMode="vertex")
                cmds.uvPathCutCtx("名前", edit=True, resetSettings=True)
    問い合わせ: cmds.uvPathCutCtx("名前", query=True, pickMode=True)

    問い合わせの戻り値 (setResult) は bool / int / float だけ。文字列を返すと kFailure
    (「Unexpected Internal Failure」) になる (ブラシで確認)。そこで選択肢 (CHOICE) は
    番号 (Setting.choices の順) で返す。編集は名前でも番号でもよい。
    """

    def __init__(self):
        super().__init__()
        self._context = None

    def makeObj(self):
        # ここで返したインスタンスが、cmds.uvPathCutCtx が返す名前のツールになる
        # コンテキストのモジュールは呼ぶときに引く (context が command を import するので、循環を避ける)
        from .context import UVPathCutContext
        self._context = UVPathCutContext()
        return self._context

    def appendSyntax(self):
        # 使えるフラグを足す。MSyntax.addFlag の引数の型は 1 つだけ
        syntax = self.syntax()
        for setting in DEFINITIONS:
            if setting.short_flag is not None:   # 色 (COLOR) はフラグを作らない (-setColor で)
                syntax.addFlag(setting.short_flag, setting.long_flag, _FLAG_TYPES[setting.kind])
        syntax.addFlag(RESET_FLAG[0], RESET_FLAG[1], om.MSyntax.kBoolean)
        syntax.addFlag(SET_COLOR_FLAG[0], SET_COLOR_FLAG[1], om.MSyntax.kString)
        syntax.addFlag(RESET_COLORS_FLAG[0], RESET_COLORS_FLAG[1], om.MSyntax.kBoolean)
        syntax.addFlag(APPLY_FLAG[0], APPLY_FLAG[1], om.MSyntax.kString)
        syntax.addFlag(CLEAR_FLAG[0], CLEAR_FLAG[1], om.MSyntax.kBoolean)
        syntax.addFlag(RUN_ACTION_FLAG[0], RUN_ACTION_FLAG[1], om.MSyntax.kString)

    def doEditFlags(self):
        parser = self.parser()
        settings = self._context.settings
        for setting in DEFINITIONS:
            flag = setting.short_flag
            if flag is None or not parser.isFlagSet(flag):
                continue
            if setting.kind == BOOL:
                value = parser.flagArgumentBool(flag, 0)
            elif setting.kind == FLOAT:
                value = parser.flagArgumentDouble(flag, 0)
            else:
                value = parser.flagArgumentString(flag, 0)
            try:
                settings.set(setting.key, value)
            except SettingsError as error:
                # 例外を投げるとコマンドのエラーになる (スクリプトエディタに赤字で出る)
                raise RuntimeError("{}: {}".format(CONTEXT_COMMAND, error))
        if parser.isFlagSet(RESET_FLAG[0]) and parser.flagArgumentBool(RESET_FLAG[0], 0):
            settings.reset()
            log.info("設定を既定に戻しました")
        if parser.isFlagSet(SET_COLOR_FLAG[0]):
            text = parser.flagArgumentString(SET_COLOR_FLAG[0], 0)
            parts = text.split(None, 1)
            try:
                if len(parts) != 2 or settings_module.definition(parts[0]).kind != COLOR:
                    raise SettingsError("「キー r g b」の形で、色の設定のキーを渡してください: {}".format(text))
                settings.set(parts[0], parts[1])
            except SettingsError as error:
                raise RuntimeError("{}: -setColor: {}".format(CONTEXT_COMMAND, error))
        if parser.isFlagSet(RESET_COLORS_FLAG[0]) and parser.flagArgumentBool(RESET_COLORS_FLAG[0], 0):
            settings.reset(keys_in_section("色"))
            log.info("色を既定に戻しました")
        if parser.isFlagSet(APPLY_FLAG[0]):
            text = parser.flagArgumentString(APPLY_FLAG[0], 0)
            try:
                operation = settings_module.normalize("operation", text)   # cut / sew (番号でも)
            except SettingsError as error:
                raise RuntimeError("{}: -apply: {}".format(CONTEXT_COMMAND, error))
            self._context.applyOperation(operation)   # モードで振り分ける (段階 16)
        if parser.isFlagSet(CLEAR_FLAG[0]) and parser.flagArgumentBool(CLEAR_FLAG[0], 0):
            self._context.clearAll()
        if parser.isFlagSet(RUN_ACTION_FLAG[0]):
            action_id = parser.flagArgumentString(RUN_ACTION_FLAG[0], 0)
            try:
                action_by_id(action_id)
            except KeyError:
                raise RuntimeError("{}: -runAction: 知らない操作です: {}".format(CONTEXT_COMMAND, action_id))
            self._context.runAction(action_id)

    def doQueryFlags(self):
        # 問い合わせは 1 回に 1 つのフラグだけ (最初に見つかったもの)
        parser = self.parser()
        settings = self._context.settings
        for setting in DEFINITIONS:
            if setting.short_flag is None or not parser.isFlagSet(setting.short_flag):
                continue
            if setting.kind == CHOICE:
                self.setResult(settings.choiceIndex(setting.key))
            elif setting.kind == FLOAT:
                self.setResult(float(settings.value(setting.key)))
            else:
                self.setResult(bool(settings.value(setting.key)))
            return


class ToolCommand(om.MPxCommand):
    """uvPathCutTool: このツールにする。

    決まった名前 (TOOL_CONTEXT) のコンテキストが無ければ作り、setToolTo する。
    毎回新しいコンテキストを作らないので、ツールの状態を保てる。
    """

    def doIt(self, args):
        if not cmds.contextInfo(TOOL_CONTEXT, exists=True):
            getattr(cmds, CONTEXT_COMMAND)(TOOL_CONTEXT)
        cmds.setToolTo(TOOL_CONTEXT)
        self.setResult(TOOL_CONTEXT)


def delete_tool_context():
    """このツールのコンテキストを消す (使っていたら選択ツールに戻してから)。

    リロードの前に呼ぶ。コンテキストのインスタンスは作ったときのクラスのままなので、
    消して作り直さないと、リロードしても古いコードが動き続ける。
    """
    if not cmds.contextInfo(TOOL_CONTEXT, exists=True):
        return False
    if cmds.currentCtx() == TOOL_CONTEXT:
        cmds.setToolTo("selectSuperContext")
    cmds.deleteUI(TOOL_CONTEXT, toolContext=True)
    return True
