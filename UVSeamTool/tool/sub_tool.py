"""
サブツール (コンテキストがマウスとキーを渡す先) の基底。
"""

from ..utils import log


class SubTool:
    """コンテキストの中の 1 つの道具 (ガイドを作る・編集する・エッジを選ぶ など)。

    コンテキストは今のサブツールのメソッドを呼ぶだけ。使わないメソッドは上書きしなくてよい。
    press / drag / release は、受け取ったら True を返す (False ならコンテキストが Maya の選択に任せる)。
    hover は、描き直しが要るなら True を返す。キーの操作のあとは、コンテキストがいつも描き直す。
    """

    # -- 公開メソッド ---------------------------------------------------------
    def activate(self):
        """このサブツールに切り替わったとき。"""

    def deactivate(self):
        """ほかのサブツールに替わる・ツールを抜けるとき。"""

    def refresh(self):
        """ガイドの組が変わった (Undo / Redo も)。持っている表示用の値を作り直す。"""

    def targetChanged(self):
        """メッシュが外から変えられた (位置・トポロジー)。グラフを使って持っているもの・途中の操作を捨てる。"""
        self.cancel()
        self.refresh()

    def hover(self, x, y):
        """ボタンを押さずにマウスを動かした。"""
        return False

    def draw(self, painter):
        """ビューを描き直すたび (tool.painter.Painter に描く)。"""

    def press(self, x, y, button, shift, ctrl):
        return False

    def drag(self, x, y):
        return False

    def release(self, x, y):
        return False

    def doubleClick(self, x, y, shift, ctrl):
        """ビューで左ボタンをダブルクリック (2 回目の押下は press に届かない)。受け取ったら True。

        受け取らなければ Maya に渡る。Maya の選択を使わないモードでは、True を返して止める。
        """
        return False

    def rightClick(self):
        """ビューで右クリック。受け取ったら True (マーキングメニューを出さない)。"""
        return False

    def applyOperation(self, operation):
        """カット / 縫合 (tool.uv_apply.CUT / SEW) のボタン。何を対象にするかはサブツールが決める。"""

    def wheel(self, steps, shift, ctrl):
        """ビューで Shift / Ctrl を押しながらホイール (steps は目盛り)。受け取ったら True (Maya に渡さない)。"""
        return False

    def splitPoints(self):
        """マーキングメニューの「切り離す」。編集のモードだけが受け取る。"""
        log.warning("切り離しは、編集のモードでガイドの点を選んでください")

    def joinGuides(self):
        """マーキングメニューの「接続する」。編集のモードだけが受け取る。"""
        log.warning("接続は、編集のモードでガイドを選んでください")

    def isBusy(self):
        """ドラッグなどの途中の操作をしているか (その間の Esc は cancel を呼ぶ)。"""
        return False

    def cancel(self):
        """途中の操作をやめる (ドラッグ中の Esc)。"""

    def complete(self):
        """Enter キー。"""

    def abort(self):
        """Esc キー。"""

    def delete(self):
        """Delete / Backspace キー。"""
