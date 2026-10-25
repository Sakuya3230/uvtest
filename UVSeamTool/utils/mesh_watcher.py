"""
メッシュが外から変えられた (動かした・変形した・トポロジーを変えた・消した) ことを知らせる。
"""

import maya.api.OpenMaya as om
import maya.utils


class MeshWatcher:
    """シェイプと、その親のトランスフォームの dirty・シェイプの削除を見て、手すきのときに on_change() を 1 回呼ぶ。

    dirty はドラッグで動かしている間などに何度も届くので、届くたびには呼ばない。最初の 1 回で executeDeferred に
    予約し、Maya が手すきになったときにまとめて 1 回だけ呼ぶ。何が変わったかは呼ばれた側が確かめる。
    親のトランスフォームも見るのは、親を動かしてもシェイプには dirty が届かないため。
    ただしレイの索引 (Mesh.rayMeshFn が持ち続ける MFnMesh) は、dirty が届いたその場で捨てる。メッシュが作り直された
    (カット・Undo など) あとに古い MFnMesh に触ると Maya が落ちるため (手すきのときまで待つと、その前のマウスの移動で触る)。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, mesh, on_change):
        self._mesh          = mesh
        self._on_change     = on_change
        self._pending       = False     # executeDeferred に予約済みか
        self._released      = False
        self._callbacks     = []

        shape_path = mesh.shapePath()
        shape      = shape_path.node()
        self._callbacks.append(om.MNodeMessage.addNodeDirtyCallback(shape, self._on_dirty))
        self._callbacks.append(om.MNodeMessage.addNodePreRemovalCallback(shape, self._on_dirty))

        # 親をワールドまでたどる (どれを動かしてもワールドの位置が変わる)
        path = om.MDagPath(shape_path)
        while path.length() > 0:
            path.pop()
            if path.length() > 0:
                self._callbacks.append(om.MNodeMessage.addNodeDirtyCallback(path.node(), self._on_dirty))

    # -- 公開メソッド ---------------------------------------------------------
    def release(self):
        """コールバックを外す (ツールを抜けるときに必ず呼ぶ。外さないとリロードのあとも古いコードが呼ばれる)。"""
        self._released = True
        for callback in self._callbacks:
            om.MMessage.removeCallback(callback)

        self._callbacks = []

    # -- 非公開メソッド -------------------------------------------------------
    def _on_dirty(self, *args):
        if self._released:
            return

        self._mesh.resetRayIndex()   # 届くたびに、その場で (安い。次にレイを当てるときに作り直す)
        if self._pending:
            return

        self._pending = True
        maya.utils.executeDeferred(self._fire)

    def _fire(self):
        self._pending = False
        if not self._released:
            self._on_change()
