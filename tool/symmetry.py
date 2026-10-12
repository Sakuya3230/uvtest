# -*- coding: utf-8 -*-
"""
対称 (段階 17)。コンテキスト (tool/context.py) に組み込む部品 (ミックスイン)。

    mirrorPlane()          今の対称の面 (Maya の対称が効いていればそれ、無ければツールの設定)
    symmetryActive()       対称が効いているか (ツールの対称か Maya の対称)
    checkMayaSymmetry()    Maya の対称の変更を見つけて表示を合わせる (0.5 秒に 1 回まで)
    mirrorFor(target)      メッシュの対応表 (効いていなければ None)
    _prebuild_mirrors()    ツールに入った直後、手すきのときに先に作る

コンテキストの属性 (settings・targets・_manip・_maya_symmetry・_maya_checked) と、
updateSelectionMirror (tool/selecting.py) を使う。仕組みは docs/17_symmetry.md。
"""
import time

from .. import log
from ..scene import mirror as scene_mirror
from . import tool_ui

__all__ = ["SymmetryMixin"]


class SymmetryMixin(object):
    """対称 (UVPathCutContext に組み込む)。"""

    def mirrorPlane(self):
        """今の対称の面 (scene.mirror.MirrorPlane)。Maya の対称の設定と、ツールの設定から。"""
        return scene_mirror.mirror_plane(self.settings.values())

    def symmetryActive(self):
        """対称が効いているか: ツールの対称がオンか、Maya の対称がオン (ワールド / オブジェクト)。"""
        return bool(self.settings.value("symmetry")) or scene_mirror.maya_plane() is not None

    def checkMayaSymmetry(self):
        """Maya の対称の設定が変わっていたら、表示を合わせる。変わっていたら True。

        Maya の対称の変更には通知が無いので、マウスを動かしたとき (syncMesh) に 0.5 秒に 1 回まで見る。
        """
        now = time.perf_counter()
        if now - self._maya_checked < 0.5:
            return False
        self._maya_checked = now
        state = scene_mirror.maya_symmetry()
        if state == self._maya_symmetry:
            return False
        first = self._maya_symmetry is None
        self._maya_symmetry = state
        if first:
            return False
        plane = scene_mirror.maya_plane(state)
        log.info("Maya の対称が変わりました: {}".format(
            "{} を使います".format(scene_mirror.plane_text(plane)) if plane is not None
            else "オフ (ツールの設定を使います)"))
        tool_ui.refresh()
        if self._manip is not None:
            self._manip.updatePreview()
            self.updateSelectionMirror()
        return True

    def mirrorFor(self, target, build=True):
        """target の対応表 (core.mirror.MirrorMap)。対称が効いていなければ None。

        覚えておいたものがあれば使う。無ければ作って、かかった時間をログに出す
        (build が False なら作らずに None)。
        """
        if target is None or not target.isValid() or not self.symmetryActive():
            return None
        return self._mirror_map(target, build)

    def _mirror_map(self, target, build=True, note=""):
        plane = self.mirrorPlane()
        started = time.perf_counter()
        mirror, cached = target.mirror(plane, build)
        if mirror is not None and not cached:
            message = "対応表 {} {} {:.0f} ms ({})".format(
                target.name(), plane, (time.perf_counter() - started) * 1000, mirror.backend)
            if note:
                message += " " + note
            log.info(message)
            if mirror.unmatched:
                log.warning("{}: 反対側が見つからない頂点が {} あります (許容値 {})".format(
                    target.name(), mirror.unmatched, plane.tolerance))
        return mirror

    def _prebuild_mirrors(self):
        """対象のメッシュの対応表を先に作る (手すきのとき。ツールを抜けていたら何もしない)。"""
        if self.targets is None:
            return
        for target in self.targets.valid():
            try:
                self._mirror_map(target, note="(先に作成)")
            except RuntimeError as error:   # メッシュが消えたなど
                log.warning("対応表を作れませんでした {}: {}".format(target.name(), error))
