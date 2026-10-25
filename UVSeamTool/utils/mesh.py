"""
ツールで使うメッシュ (トランスフォームで指す)。
"""

import hashlib

import maya.api.OpenMaya as om

from ..compat.accel import np
from . import node


class Mesh:
    """メッシュを持つトランスフォーム 1 つ。

    トランスフォームで指し、シェイプは使うときに引く。名前ではなく MObjectHandle と MDagPath を持つので、
    名前を変えられても同じメッシュを指す。読んだ値は numpy の配列で返す (core に Maya の型を渡さない)。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, transform_path):
        self._handle    = om.MObjectHandle(transform_path.node())
        self._dag_path  = om.MDagPath(transform_path)
        self._ray_fn    = None      # レイを当てるための (MFnMesh, 索引の作り方)。rayMeshFn で作り、resetRayIndex で捨てる

    def __repr__(self):
        return "Mesh({!r})".format(self.fullPath() if self.isValid() else "<deleted>")

    # -- クラスメソッド -------------------------------------------------------
    @classmethod
    def fromName(cls, name):
        """トランスフォーム (かそのシェイプ) の名前から作る。メッシュでなければ ValueError。"""
        transform_path = node.mesh_transform_path(node.dag_path_from_name(name))
        if transform_path is None:
            raise ValueError("メッシュではありません: {}".format(name))

        return cls(transform_path)

    # -- 公開メソッド ---------------------------------------------------------
    def key(self):
        """このメッシュを表す数 (名前を変えても変わらない。ガイドの組の鍵に使う)。"""
        return self._handle.hashCode()

    def isValid(self):
        """ノードが消されていないか。"""
        return self._handle.isValid()

    def dagPath(self):
        """トランスフォームの MDagPath (写し)。"""
        return om.MDagPath(self._dag_path)

    def shapePath(self):
        """シェイプの MDagPath。"""
        return node.mesh_shape_path(self._dag_path)

    def fullPath(self):
        """トランスフォームのフルパス (cmds に渡す名前)。"""
        return node.full_path(self._dag_path)

    def name(self):
        """トランスフォームの名前だけ (表示用)。"""
        return node.short_name(self._dag_path)

    def isShapeLocked(self):
        """シェイプがロック (lockNode) されているか。ロックされていると UV を変えられない・アトリビュートを足せない。"""
        return om.MFnDependencyNode(self.shapePath().node()).isLocked

    def instanceCount(self):
        """シェイプを共有しているインスタンスの数 (インスタンスでなければ 1)。"""
        return om.MFnDagNode(self.shapePath()).instanceCount(False)

    def uvCount(self):
        """今の UV セットの UV の数。"""
        return self._mesh_fn().numUVs()

    def points(self):
        """頂点の位置 (N, 3) の配列 (オブジェクト空間)。"""
        mesh = self._mesh_fn()

        return np.array([(p.x, p.y, p.z) for p in mesh.getPoints(om.MSpace.kObject)])

    def worldPoints(self):
        """頂点の位置 (N, 3) の配列 (ワールド空間。描画用)。"""
        mesh = self._mesh_fn()

        return np.array([(p.x, p.y, p.z) for p in mesh.getPoints(om.MSpace.kWorld)])

    def edgeVertices(self):
        """エッジの両端の頂点 (M, 2) の配列。行の番号がエッジの番号。"""
        mesh = self._mesh_fn()

        # API 2.0 にはエッジをまとめて読む関数が無いので 1 本ずつ読む
        return np.array([mesh.getEdgeVertices(edge) for edge in range(mesh.numEdges)], dtype=np.int64)

    def faceVertices(self):
        """面ごとの頂点の (数 (F,), 並び (角の数,)) の配列。getVertices は全部の面をまとめて読める。"""
        counts, connects = self._mesh_fn().getVertices()

        return np.array(counts, dtype=np.int64), np.array(connects, dtype=np.int64)

    def assignedUVs(self):
        """面の角ごとの UV の (面ごとの数 (F,), UV の番号 (角の数,)) の配列 (今の UV セット。UV の無い面は数が 0)。"""
        uv_counts, uv_ids = self._mesh_fn().getAssignedUVs()

        return np.array(uv_counts, dtype=np.int64), np.array(uv_ids, dtype=np.int64)

    def connectionKey(self, face_vertices=None):
        """面ごとの頂点の並びのハッシュ (文字列)。つながりが変わったかを、エッジを読まずに安く確かめるため。

        エッジを 1 本ずつ読む edgeVertices よりずっと速い。face_vertices (faceVertices() の結果) を渡せば読み直さない。
        """
        counts, connects = face_vertices if face_vertices is not None else self.faceVertices()
        digest           = hashlib.sha1(counts.tobytes())
        digest.update(connects.tobytes())

        return digest.hexdigest()

    def worldMatrix(self):
        """シェイプのワールドの行列 (4 x 4 の numpy の配列。行ベクトル: ワールドの位置 = [x, y, z, 1] @ 行列)。"""
        return np.array(list(self.shapePath().inclusiveMatrix()), dtype=float).reshape(4, 4)

    def rayMeshFn(self):
        """レイを当てる (allIntersections) ための (MFnMesh, accelParams)。初めて使うときに作って使い回す。

        索引 (accelParams = autoUniformGridParams。面を格子に分けた表) は MFnMesh の中に作られるので、
        同じ MFnMesh を持ち続けないと毎回作り直しになる (24 万面で 1 回のレイが 16 ms -> 0.01 ms。作る最初の 1 回は 40 ms ほど)。
        形・位置が変わったら resetRayIndex で捨てる (古い索引のままだと、動かす前の形に当たる)。
        """
        if self._ray_fn is None:
            mesh_fn      = om.MFnMesh(self.shapePath())
            self._ray_fn = (mesh_fn, mesh_fn.autoUniformGridParams())

        return self._ray_fn

    def resetRayIndex(self):
        """rayMeshFn の索引を捨てる (メッシュの形・位置・つながりが変わったとき)。"""
        self._ray_fn = None

    def edgeNames(self, edges):
        """エッジの番号 -> cmds に渡す名前のリスト ("|pSphere1.e[3]")。"""
        path = self.fullPath()

        return ["{}.e[{}]".format(path, edge) for edge in edges]

    # -- 非公開メソッド -------------------------------------------------------
    def _mesh_fn(self):
        return om.MFnMesh(self.shapePath())
