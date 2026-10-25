"""
今のガイドの組を、メッシュごとに持つ置き場所 (ツールを抜けても残る)。
"""

from __future__ import annotations

from .guide_set import GuideSet

_EMPTY = GuideSet()


class GuideStore:
    """メッシュの鍵 (utils.mesh.Mesh.key) -> 今のガイドの組。

    変えるのは Undo のコマンド (tool.guide_edit) だけ。変わったらリスナーに知らせる (Undo / Redo でも)。
    シーンには tool.guide_storage がシェイプのアトリビュートに保存する (ここは読んだものの写し。リロードすると空になり、
    次に TargetMesh を作るときにアトリビュートから読み直す)。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self):
        self._sets      = {}
        self._listeners = []

    # -- 公開メソッド ---------------------------------------------------------
    def guideSet(self, key):
        """そのメッシュの今のガイドの組 (無ければ空の組)。"""
        return self._sets.get(key, _EMPTY)

    def setGuideSet(self, key, guide_set):
        self._sets[key] = guide_set
        for listener in list(self._listeners):
            listener(key)

    def addListener(self, listener):
        """listener(key) を、ガイドの組が変わるたびに呼ぶ。"""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def removeListener(self, listener):
        if listener in self._listeners:
            self._listeners.remove(listener)


_STORE = GuideStore()


def store():
    """パッケージに 1 つの GuideStore。"""
    return _STORE
