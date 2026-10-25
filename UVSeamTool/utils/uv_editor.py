"""
UV をカット / 縫合する (Maya のコマンドを呼ぶだけ)。

受け取るのはメッシュ (utils.mesh.Mesh) とエッジの番号だけ。ガイドのことは知らない。
polyMapCut / polyMapSew は終わると操作したエッジを選択に足すので、呼ぶ前後で選択を元に戻す
(エッジを選ぶのはツールを抜けるときだけ。tool.exit_selection)。
"""

from contextlib import contextmanager

import maya.api.OpenMaya as om
import maya.cmds as cmds


def cut_edges(mesh, edges):
    """エッジで UV を切り離す。選択は変えない。"""
    if edges:
        with _keep_selection():
            cmds.polyMapCut(mesh.edgeNames(edges))


def sew_edges(mesh, edges):
    """エッジで UV を縫い合わせる。選択は変えない。"""
    if edges:
        with _keep_selection():
            cmds.polyMapSew(mesh.edgeNames(edges))


@contextmanager
def _keep_selection():
    # 中のコマンドが選択を変えても、出るときに元の選択 (オブジェクトもコンポーネントも) に戻す
    before = om.MGlobal.getActiveSelectionList()
    try:
        yield
    finally:
        om.MGlobal.setActiveSelectionList(before, om.MGlobal.kReplaceList)
