"""
対象のメッシュの見張り (外からの変更・選んだメッシュを足す・エッジの選択モードを保つ)。
"""

import maya.cmds as cmds
import maya.utils

from ..utils import log, view
from ..utils.mesh_watcher import MeshWatcher
from ..utils.selection import enter_edge_mode, is_edge_mode, selected_meshes
from ..utils.selection_watcher import SELECT_MODE, SelectionWatcher
from . import mesh_checks
from .target_mesh import TOPOLOGY, UNCHANGED, UV


class TargetWatch:
    """ツールを使っている間、対象のメッシュ (tool.targets.Targets) を見張る。

    - メッシュが外から変えられたら (MeshWatcher)、TargetMesh を読み直して on_changed() を呼ぶ (UV だけなら描き直すだけ)。
      消されたメッシュは対象から外し、全部消えたらツールを抜ける
    - ツールを使っている間に選んだメッシュは (SelectionWatcher)、対象に加えて on_changed() を呼ぶ
    - 選択のモード・種類が替えられたら (ホットキー・マーキングメニュー・ステータスラインのボタンなど)、エッジの選択モードに戻す
    on_changed は、サブツールに対象が変わったことを知らせる関数 (コンテキストが渡す)。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, targets, on_changed):
        self._targets       = targets
        self._on_changed    = on_changed
        self._own_mode      = False     # 自分でエッジの選択モードにしている間 (その知らせでは戻さない)
        self._watchers      = {target.key(): MeshWatcher(target.mesh(), self._mesh_listener(target.key()))
                               for target in targets}
        self._selection     = SelectionWatcher(self._on_selection_changed)
        self._select_mode   = SelectionWatcher(self._on_select_mode_changed, SELECT_MODE)

    # -- 公開メソッド ---------------------------------------------------------
    def release(self):
        """見張りをすべて外す (ツールを抜けるときに必ず呼ぶ)。"""
        for watcher in self._watchers.values():
            watcher.release()
        self._watchers = {}
        self._selection.release()
        self._select_mode.release()

    # -- 非公開メソッド -------------------------------------------------------
    def _on_selection_changed(self):
        # 選択が変わった (手すきのときに 1 回)。選んだメッシュのうち、まだ対象でないものを加える
        added = []
        for mesh in selected_meshes():
            target = self._targets.add(mesh)
            if target is not None:
                self._watchers[target.key()] = MeshWatcher(mesh, self._mesh_listener(target.key()))
                mesh_checks.report(mesh)
                added.append(mesh)

        if added:
            self._enter_edge_mode()
            log.info("対象に加えました: {}".format(", ".join(mesh.name() for mesh in added)))
            view.refresh()

    def _on_select_mode_changed(self):
        # 選択のモード・種類が替えられた (手すきのときに 1 回)。エッジの選択モードに戻す
        if self._own_mode or is_edge_mode([target.mesh() for target in self._targets]):
            return   # 自分で替えた知らせか、エッジのまま (選択の優先度だけ変わったなど)

        self._enter_edge_mode()
        log.info("ツールを使っている間はエッジの選択モードです")

    def _enter_edge_mode(self):
        # 対象のメッシュすべてをエッジの選択モードにする。そのために届く知らせ (次の手すきのとき) では戻さない
        self._own_mode = True
        enter_edge_mode([target.mesh() for target in self._targets])
        maya.utils.executeDeferred(self._end_own_mode)

    def _end_own_mode(self):
        self._own_mode = False

    def _mesh_listener(self, key):
        # MeshWatcher に渡す関数 (どのメッシュの知らせかを key で覚える)
        return lambda: self._on_mesh_changed(key)

    def _on_mesh_changed(self, key):
        # メッシュが外から変えられた (手すきのときに 1 回)
        target = self._targets.find(key)
        if target is None:
            return

        if not target.mesh().isValid():
            # 消されたメッシュは対象から外す。全部消えたらツールを抜ける
            self._watchers.pop(key).release()
            self._targets.remove(key)
            self._on_changed()
            if len(self._targets) == 0:
                log.warning("対象のメッシュがすべて消されたので、ツールを抜けます")
                maya.utils.executeDeferred(cmds.setToolTo, "selectSuperContext")
            else:
                log.warning("消されたメッシュを対象から外しました")
            view.refresh()
            return

        change = target.sync()
        if change == UNCHANGED:
            return

        if change != UV:   # UV だけなら切れ目の縁取りだけが変わった (グラフは同じなので、サブツールには知らせない)
            self._on_changed()

        if change == TOPOLOGY:
            log.info("{}: トポロジーが変わったので読み直しました".format(target.mesh().name()))
        elif change != UV:
            log.debug("{}: 位置が変わったので読み直しました".format(target.mesh().name()))

        view.refresh()
