"""
スクリプトエディタにメッセージを出す (レベル付き)。

    log.debug("...")     開発のときだけ見たいもの (クリックした頂点・作った区間 など)
    log.info("...")      使う人にも見せる結果 (カットした など)
    log.warning("...")   思ったとおりにできなかったこと (メッシュを選んでいない など)
    log.error("...")     ツールの不具合・続けられない失敗

今のレベルより下のものは出さない。レベルは環境変数に持つので、モジュールをリロードしても変わらない
(Maya を閉じると既定 constants.DEFAULT_LOG_LEVEL に戻る)。

    log.set_level(log.DEBUG)   # 開発のとき
"""

import os

import maya.api.OpenMaya as om

from ..constants import DEFAULT_LOG_LEVEL, LOG_LEVEL_ENV, TOOL_NAME

DEBUG   = 10
INFO    = 20
WARNING = 30
ERROR   = 40

_NAMES = {DEBUG: "DEBUG", INFO: "INFO", WARNING: "WARNING", ERROR: "ERROR"}


def level():
    """今のレベル (DEBUG / INFO / WARNING / ERROR)。"""
    return _parse(os.environ.get(LOG_LEVEL_ENV, DEFAULT_LOG_LEVEL))


def set_level(new_level):
    """レベルを変える。数 (log.DEBUG など) か名前 ("DEBUG" など)。"""
    os.environ[LOG_LEVEL_ENV] = _NAMES[_parse(new_level)]


def debug(message):
    if level() <= DEBUG:
        om.MGlobal.displayInfo(_format("[DEBUG] ", message))


def info(message):
    if level() <= INFO:
        om.MGlobal.displayInfo(_format("", message))


def warning(message):
    if level() <= WARNING:
        om.MGlobal.displayWarning(_format("", message))


def error(message):
    if level() <= ERROR:
        om.MGlobal.displayError(_format("", message))


def _format(prefix, message):
    return "{}{}: {}".format(prefix, TOOL_NAME, message)


def _parse(value):
    # 名前・数のどちらでも受け取る。知らない値なら ValueError
    if isinstance(value, str):
        for number, name in _NAMES.items():
            if name == value.upper():
                return number
        raise ValueError("ログのレベルの名前ではありません: {}".format(value))

    if value not in _NAMES:
        raise ValueError("ログのレベルではありません: {}".format(value))

    return value
