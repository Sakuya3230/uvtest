"""
Maya の選択 (選んだもの・選択のモード) が変わったことを知らせる。
"""

import maya.api.OpenMaya as om
import maya.utils

SELECTION   = ("SelectionChanged",)                         # 選んだものが変わった
SELECT_MODE = ("SelectModeChanged", "SelectTypeChanged")    # 選択のモード (オブジェクト / コンポーネント)・種類が変わった


class SelectionWatcher:
    """events (MEventMessage のイベントの名前) が届いたら、手すきのときに on_change() を 1 回呼ぶ。

    矩形選択などで続けて届いても、最初の 1 回で executeDeferred に予約し、まとめて 1 回だけ呼ぶ。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, on_change, events=SELECTION):
        self._on_change = on_change
        self._pending   = False
        self._released  = False
        self._callbacks = [om.MEventMessage.addEventCallback(name, self._on_event) for name in events]

    # -- 公開メソッド ---------------------------------------------------------
    def release(self):
        """コールバックを外す (ツールを抜けるときに必ず呼ぶ)。"""
        self._released = True
        for callback in self._callbacks:
            om.MMessage.removeCallback(callback)
        self._callbacks = []

    # -- 非公開メソッド -------------------------------------------------------
    def _on_event(self, *args):
        if self._pending or self._released:
            return

        self._pending = True
        maya.utils.executeDeferred(self._fire)

    def _fire(self):
        self._pending = False
        if not self._released:
            self._on_change()
