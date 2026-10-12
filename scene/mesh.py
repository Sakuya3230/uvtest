# -*- coding: utf-8 -*-
"""
対象のメッシュと、エッジの選択モード。

段階 2:
    shape = target_mesh()                 # 選択 (かハイライト) の最初のメッシュのシェイプ
    enter_edge_mode(shape_transform(shape))   # そのメッシュをエッジの選択モードにする
段階 3:
    model = MeshModel(shape)              # MFnMesh を使い回し、メッシュが変わったら作り直す
    hit = model.hit(source, direction)    # レイが当たる表の面 (core.picking.FaceHit)
    model.release()                       # コールバックを外す
段階 5:
    graph = model.graph()                 # 頂点とエッジのグラフ (core.graph.MeshGraph。1 回だけ作る)
段階 14:
    shapes = target_meshes()              # 対象にするメッシュすべて (選択とハイライト)
    enter_edge_mode([transform, ...])     # まとめてエッジの選択モードにする
段階 16:
    loop = edge_loop(shape, edge)         # ダブルクリックで選ばれるループ (選択は変えない)
    model.edgeLoop(edge)                  # 同じ (トポロジーが同じ間は覚えておく)
    model.edgeSegments(edges)             # エッジの両端の位置 [(p0, p1)] (描くため)
段階 18:
    edit_blocker(shape)                   # UV を変えられない理由 (シェイプのロック)。変えられれば None
    mesh_notes(shape)                     # 知らせておくこと [(警告か, 文)] (インスタンス・UV が無い)
段階 13:
    kind = model.sync()                   # 外部の変更を調べ、変わっていればグラフを作り直す (core.sync.CHANGE_*)
    model.topologyKey()                   # 今のグラフのトポロジーの鍵
    model.name()                          # シェイプの今のフルパス (名前を変えられても追う)

仕組み:
- 対象は「選んでいるもの」の中の最初のメッシュ。オブジェクトとして選んでいても、
  コンポーネント (頂点・エッジ) を選んでいてもよい。cmds.ls(objectsOnly=True) は、
  コンポーネントならそのシェイプの名前を返す。何も選んでいなければ、ハイライトしている
  (コンポーネントの選択モードにしている) メッシュ
- Transform の下には、スキンなどで中間オブジェクト (intermediateObject。変形の元の形) の
  シェイプもある。中間オブジェクトは見えないので飛ばし、表示されているシェイプを使う
- 選択のモード・マスク (selectMode / selectType) は GUI の状態。mayapy では切り替えても残らない
"""
import maya.api.OpenMaya as om
import maya.cmds as cmds

from ..core.graph import MeshGraph
from ..core.picking import FaceHit
from ..core.section import SectionTopology
from ..core.sync import CHANGE_NONE, CHANGE_POINTS, CHANGE_TOPOLOGY, classify, topology_key

__all__ = ["mesh_shape", "target_mesh", "target_meshes", "shape_transform", "enter_edge_mode", "mesh_counts",
           "dag_path", "mesh_graph", "edit_blocker", "mesh_notes", "mesh_topology_key", "world_points", "edge_loop", "MeshModel"]


def dag_path(name):
    """名前の MDagPath。"""
    sel = om.MSelectionList()
    sel.add(name)
    return sel.getDagPath(0)


def mesh_shape(name):
    """name (Transform かメッシュのシェイプ) の、表示されているメッシュのシェイプのフルパス。

    メッシュでなければ (中間オブジェクトなら) None。Transform なら、中間オブジェクトでない
    最初のメッシュのシェイプ。
    """
    if not cmds.objExists(name):
        return None
    if cmds.nodeType(name) == "mesh":
        if cmds.getAttr(name + ".intermediateObject"):
            return None
        return (cmds.ls(name, long=True) or [None])[0]
    shapes = cmds.listRelatives(name, shapes=True, type="mesh", fullPath=True,
                                noIntermediate=True) or []
    return shapes[0] if shapes else None


def target_meshes():
    """ツールの対象にするメッシュのシェイプのフルパスすべて (段階 14。無ければ [])。

    選んでいるもの (オブジェクトでもコンポーネントでもよい) のメッシュと、ハイライトしている
    (コンポーネントの選択モードにしている) メッシュ。選んでいる順、次にハイライトの順。重複なし。
    """
    shapes = []
    for names in (cmds.ls(selection=True, objectsOnly=True, long=True),
                  cmds.ls(hilite=True, long=True)):
        for name in names or []:
            shape = mesh_shape(name)
            if shape and shape not in shapes:
                shapes.append(shape)
    return shapes


def target_mesh():
    """ツールの対象にするメッシュのシェイプのフルパス (最初の 1 つ。無ければ None)。"""
    shapes = target_meshes()
    return shapes[0] if shapes else None


def shape_transform(shape):
    """シェイプの親の Transform のフルパス。"""
    parents = cmds.listRelatives(shape, parent=True, fullPath=True) or []
    return parents[0] if parents else shape


def enter_edge_mode(transform):
    """メッシュ (Transform。リストで複数でもよい) をエッジの選択モードにする
    (右クリックのマーキングメニューの「エッジ」と同じ)。

    Maya の MEL の doMenuComponentSelection は、マーキングメニューを一度も使っていないと
    読み込まれておらず「Cannot find procedure」になる (ウェイトスライダーで確認) ので、
    同じこと (doMenuComponentSelectionExt の中身) を cmds で行う:
      オブジェクトの選択モード    ハイライトしたオブジェクト用のマスク (-objectComponent) を
                                  全部オフにしてエッジだけオン、そのオブジェクトをハイライト
      コンポーネントの選択モード  マスクを全部オフにしてエッジだけオン、ハイライト
    """
    if cmds.selectMode(query=True, object=True):
        cmds.selectType(objectComponent=True, allComponents=False)
        cmds.selectType(objectComponent=True, edge=True)
        cmds.selectType(edge=True)
    else:
        cmds.selectType(allComponents=False)
        cmds.selectType(edge=True)
    cmds.hilite(transform)


def edit_blocker(shape):
    """UV をカット / 縫合できない理由 (文)。できれば None (段階 18)。

    シェイプがロック (lockNode) されていると polyMapCut / polyMapSew は失敗し、MDGModifier からは
    「Unexpected Internal Failure」としか分からない (mayapy で確認)。前もって調べて理由を出す。
    Transform だけのロック・リファレンスのメッシュはカットできる (mayapy で確認)。
    """
    if not cmds.objExists(shape):
        return "メッシュがありません"
    if (cmds.lockNode(shape, query=True, lock=True) or [False])[0]:
        return "シェイプがロックされています (lockNode)"
    return None


def mesh_notes(shape):
    """ツールの対象にするときに知らせること [(警告か, 文)] (段階 18)。"""
    notes = []
    parents = cmds.listRelatives(shape, allParents=True, fullPath=True) or []
    if len(parents) > 1:
        notes.append((False, "インスタンスです。カット / 縫合すると、ほかのインスタンス ({} 個) も"
                             "同じに変わります".format(len(parents) - 1)))
    if not cmds.polyEvaluate(shape, uv=True):
        notes.append((True, "UV がありません (カット / 縫合しても変わりません)"))
    blocker = edit_blocker(shape)
    if blocker:
        notes.append((True, blocker + "。パスの確定・選択はできますが、カット / 縫合はできません"))
    return notes


def mesh_counts(shape):
    """(頂点の数, エッジの数, フェースの数)。"""
    fn = om.MFnMesh(dag_path(shape))
    return fn.numVertices, fn.numEdges, fn.numPolygons


def _xyz(point):
    return (point.x, point.y, point.z)


def mesh_graph(fn):
    """MFnMesh (ワールドの位置) から core.graph.MeshGraph を作る。

    エッジの両端は getEdgeVertices で 1 本ずつ読む (API 2.0 にまとめて読む関数が無い。
    4.5 万頂点・9 万エッジで 100 ms ほど。numpy / scipy でも速くならない)。
    """
    points = [(p.x, p.y, p.z) for p in fn.getPoints(om.MSpace.kWorld)]
    edges = [tuple(fn.getEdgeVertices(e)) for e in range(fn.numEdges)]
    return MeshGraph(points, edges)


def edge_loop(shape, edge):
    """エッジ edge から選択の「ダブルクリック」と同じループ (エッジの番号のリスト。重複なし)。

    Maya のエッジのダブルクリックは、境界のエッジなら境界の一周、それ以外ならエッジのループを選ぶ。
    polySelect -edgeLoopOrBorder が同じ選び方をする (MEL の polySelectEdgesEveryN "edgeLoopOrBorder")。
    noSelection で、選択を変えずに番号だけを返す。閉じたループは最初の番号が最後にも入るので除く。
    """
    result = cmds.polySelect(shape, edgeLoopOrBorder=edge, noSelection=True) or []
    loop = []
    for index in result:
        if index not in loop:
            loop.append(index)
    return loop or [edge]


def world_points(fn):
    """頂点のワールドの位置 [(x, y, z)] (getPoints でまとめて読む)。"""
    return [(p.x, p.y, p.z) for p in fn.getPoints(om.MSpace.kWorld)]


def mesh_topology_key(fn):
    """トポロジーの鍵 (core.sync.topology_key)。getVertices で面ごとの頂点をまとめて読む。"""
    counts, connects = fn.getVertices()
    return topology_key(counts, connects, fn.numVertices)


class MeshModel(object):
    """対象のメッシュの状態をまとめて持つ (段階 3。グラフ・外部の変更・対称の対応表は後の段階で足す)。

    MFnMesh は作り直すと、交点の索引 (autoUniformGridParams) も作り直しになって遅いので
    使い回す。ただし、メッシュが変わる (シェイプが dirty になる) と、前に作った MFnMesh /
    MItMeshPolygon は使えなくなる。ヒストリーのあるメッシュを polyMapCut したあとに古い
    MFnMesh を使うと、何を読んでも (getPoint でも) Maya が落ちた (旧版で確認。古いものを
    捨てるだけなら落ちない)。そこで、シェイプの dirty の通知 (addNodeDirtyCallback) で
    捨てておき、次に使うときに作り直す (fn プロパティ)。

    使い終わったら release() でコールバックを外す (外さないと、ツールを抜けても呼ばれ続け、
    リロードしたあとは古いコードが呼ばれる)。
    """

    def __init__(self, shape):
        self.path = dag_path(shape)   # MItMeshPolygon は参照を保持しないので、ここで持つ
        self._fn = None
        self._polygons = None
        self._accel = None
        self._graph = None   # core.graph.MeshGraph (graph() で作る)
        self._key = None     # グラフを作ったときのトポロジーの鍵 (段階 13)
        self._changed = False   # 通知が来た (変わったかもしれない)。sync() で中身を比べる
        self._loops = {}        # エッジ -> ループ (edgeLoop。トポロジーが変わったら捨てる。段階 16)
        self._section = None    # (トポロジーの鍵, SectionTopology) (輪切り。段階 19)
        # シェイプの dirty (頂点・トポロジー・UV・変形) と、ワールドの行列の変更 (自分か親の
        # Transform の移動。シェイプは dirty にならない) を受け取る
        self._callbacks = [
            om.MNodeMessage.addNodeDirtyCallback(self.path.node(), self._on_dirty),
            om.MDagMessage.addWorldMatrixModifiedCallback(self.path, self._on_dirty),
        ]

    @property
    def shape(self):
        return self.name()

    def name(self):
        """シェイプの今のフルパス (名前を変えられても、MDagPath が今の名前を返す)。"""
        return self.path.fullPathName()

    def _on_dirty(self, *args):
        # ここでは「変わったかも」の印を付けて古いものを捨てるだけ。重い比較は sync() で
        # (dirty は 1 回のカットで何度も届く。通知の中で Maya を読むのも避ける)
        self._changed = True
        self._fn = None   # 次に使うときに作り直す
        self._polygons = None
        self._accel = None

    def sync(self):
        """外部の変更を調べる (段階 13)。変わっていればグラフを作り直し、変更の種類を返す。

        通知 (dirty・ワールドの行列) が無ければ何も読まずに CHANGE_NONE。あれば、トポロジーの鍵と
        頂点の位置を前のグラフと比べる:
            CHANGE_NONE       UV のカット / 縫合など (位置もトポロジーも同じ)
            CHANGE_POINTS     位置だけ: 同じエッジで位置を替えたグラフ (MeshGraph.withPoints)
            CHANGE_TOPOLOGY   つながりが変わった: グラフを読み直す
        メッシュが消えていれば何もしない (印は残すので、Undo で戻ったら調べる)。
        """
        if not self._changed or self._graph is None:
            return CHANGE_NONE
        if not self.isValid():
            return CHANGE_NONE
        self._changed = False
        fn = self.fn
        key = mesh_topology_key(fn)
        points = world_points(fn) if key == self._key else None
        kind = classify(self._key, key, self._graph.points, points if points is not None else [])
        if kind == CHANGE_TOPOLOGY:
            self._graph = mesh_graph(fn)
            self._key = key
            self._loops = {}
        elif kind == CHANGE_POINTS:
            self._graph = self._graph.withPoints(points)
        return kind

    def localPoints(self):
        """頂点のオブジェクトの空間の位置 [(x, y, z)] (オブジェクトの空間の対称のため。段階 17)。"""
        return [(p.x, p.y, p.z) for p in self.fn.getPoints(om.MSpace.kObject)]

    def edgeLoop(self, edge):
        """edge からのループ (edge_loop)。トポロジーが同じ間は覚えておく (位置が変わってもループは同じ)。"""
        loop = self._loops.get(edge)
        if loop is None:
            loop = self._loops[edge] = edge_loop(self.name(), edge)
        return loop

    def sectionTopology(self):
        """輪切りの断面に使う、エッジとフェースの対応 (core.section.SectionTopology。段階 19)。

        トポロジーが同じ間は覚えておく (位置が変わっても同じ)。
        """
        key = self.topologyKey()
        if self._section is None or self._section[0] != key:
            counts, connects = self.fn.getVertices()
            self._section = (key, SectionTopology(self.graph().edges, list(counts), list(connects)))
        return self._section[1]

    def edgeSegments(self, edges):
        """エッジの両端のワールドの位置 [(p0, p1)] (ループを描くため。段階 16)。"""
        fn = self.fn
        segments = []
        for edge in edges:
            a, b = fn.getEdgeVertices(edge)
            segments.append((self.point(a), self.point(b)))
        return segments

    def topologyKey(self):
        """今のグラフのトポロジーの鍵 (グラフを作っていなければ作る)。"""
        self.graph()
        return self._key

    def isValid(self):
        """メッシュがまだシーンにあるか (消したら False。Undo で戻れば同じノードなので True に戻る)。

        MObjectHandle.isValid は、ノードが消されて Undo のキューにだけ残っているときも False。
        消えたメッシュの MFnMesh を作ったり、消えたシェイプへ確定したりするとエラーになるので、
        拾う・描く・確定する前に確かめる。
        """
        return om.MObjectHandle(self.path.node()).isValid() and self.path.isValid()

    def release(self):
        for callback in self._callbacks:
            om.MMessage.removeCallback(callback)
        self._callbacks = []
        self._on_dirty()
        self._changed = False

    @property
    def fn(self):
        """MFnMesh (メッシュが変わっていたら作り直す)。"""
        if self._fn is None:
            self._fn = om.MFnMesh(self.path)
            self._accel = self._fn.autoUniformGridParams()   # 交点を探す索引の作り方
            self._polygons = om.MItMeshPolygon(self.path)
        return self._fn

    def graph(self):
        """頂点とエッジのグラフ (最初に使うときに 1 回だけ作る)。

        UV をカット / 縫合してもグラフ (頂点・位置・エッジ) は変わらないので、dirty では捨てない。
        メッシュの変形・トポロジーの変更で作り直すのは sync() (段階 13)。
        """
        if self._graph is None:
            fn = self.fn
            self._graph = mesh_graph(fn)
            self._key = mesh_topology_key(fn)
            self._changed = False   # 今の中身で作ったので、それまでの通知は見なくてよい
        return self._graph

    def point(self, vertex):
        """頂点のワールドの位置 (タプル)。"""
        return _xyz(self.fn.getPoint(vertex, om.MSpace.kWorld))

    def face_vertices(self, face):
        return list(self.fn.getPolygonVertices(face))

    def face_edges(self, face):
        """面の辺 [(エッジの番号, 頂点 0, 頂点 1)]。

        辺の番号は MItMeshPolygon.getEdges で読み、両端は getEdgeVertices で読む
        (面の辺の並びと角の並びの対応には頼らない)。
        """
        fn = self.fn   # dirty なら、ここで MItMeshPolygon も作り直す
        self._polygons.setIndex(face)
        return [(edge,) + tuple(fn.getEdgeVertices(edge)) for edge in self._polygons.getEdges()]

    def hit(self, source, direction, front_only=True):
        """レイ (始点・向き。MPoint / MVector かタプル) が当たる面 (core.picking.FaceHit)。

        front_only (既定) なら、裏の面 (法線がレイと同じ向き) は飛ばして、その奥で最初の
        表の面を使う。allIntersections (sortHits=True) は近い順の交点を返し、外れたら None。
        front_only でなければ、最初に当たった面 (closestIntersection。裏の面でもよい)。
        当たらなければ None。
        """
        fn = self.fn   # dirty なら、ここで作り直す (索引も)
        ray_source = om.MFloatPoint(*tuple(source)[:3])
        ray_direction = om.MFloatVector(*tuple(direction)[:3])
        if front_only:
            result = fn.allIntersections(ray_source, ray_direction, om.MSpace.kWorld,
                                         1.0e7,    # この距離まで探す
                                         False,    # 逆向きのレイは探さない
                                         accelParams=self._accel, sortHits=True)
            hits = list(zip(result[0], result[2])) if result is not None else []
        else:
            result = fn.closestIntersection(ray_source, ray_direction, om.MSpace.kWorld,
                                            1.0e7, False, accelParams=self._accel)
            hits = [(result[0], result[2])] if result is not None and result[2] >= 0 else []
        ray = om.MVector(*tuple(direction)[:3])
        for point, face in hits:
            # 法線とレイが向き合っていれば (内積が負) 表の面
            front = fn.getPolygonNormal(face, om.MSpace.kWorld) * ray < 0.0
            if front or not front_only:
                vertices = self.face_vertices(face)
                corners = [self.point(v) for v in vertices]
                return FaceHit(face, (point.x, point.y, point.z), vertices, corners, front)
        return None
