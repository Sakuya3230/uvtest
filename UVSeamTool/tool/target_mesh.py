"""
ツールの対象のメッシュ (サブツールが共有する、読んだデータ)。
"""

from ..compat.accel import np
from ..core.guide import guide_store
from ..core.path.edge_topology import EdgeTopology
from ..core.path.mesh_graph import MeshGraph
from ..core.path.topology import topology_of
from ..core.settings import settings
from ..core.seam.uv_seams import uv_seam_mask
from ..core.symmetry.mirror_map import MirrorMap
from ..utils import log
from . import guide_storage

UNCHANGED   = None
MOVED       = "moved"       # 位置だけが変わった (動かした・変形した)
TOPOLOGY    = "topology"    # つながりが変わった
UV          = "uv"          # UV の切れ目だけが変わった (カット / 縫合・その Undo)



class TargetMesh:
    """対象のメッシュ 1 つと、そこから読んで作ったもの (グラフ・描画用の位置・トポロジーの目印・UV の切れ目)。

    作るときに、シェイプに保存したガイドを読んで guide_store に入れる (トポロジーが違えば使わない)。
    メッシュが外から変えられたら sync() で読み直す (コンテキストが utils.mesh_watcher の知らせで呼ぶ)。
    作成と編集のサブツールは同じ TargetMesh を受け取って使う。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, mesh):
        self._mesh              = mesh
        self._key               = mesh.key()
        self._connection_key    = None      # 面ごとの頂点の並びのハッシュ (つながりが変わったかを安く確かめる)
        self._points            = None      # オブジェクト空間の位置 (グラフの長さ)
        self._edges             = None
        self._graph             = None
        self._topology          = None
        self._world_points      = None      # 頂点の番号 -> ワールドの位置 (描画用)
        self._uv_seams          = None      # エッジごとに UV の切れ目なら True (描画用)
        self._face_vertices     = None      # 面ごとの頂点の (数, 並び) の配列
        self._edge_topology     = None      # EdgeTopology (選択のモードで使うときに作る。トポロジーが変わったら捨てる)
        self._mirror_maps       = {}        # 対称の面 -> MirrorMap (使うときに作る。位置・トポロジーが変わったら捨てる)

        self._read_all()

    # -- 公開メソッド ---------------------------------------------------------
    def mesh(self):
        """utils.mesh.Mesh。"""
        return self._mesh

    def key(self):
        """ガイドの組の鍵。"""
        return self._key

    def graph(self):
        return self._graph

    def topology(self):
        """トポロジーの目印 (保存するガイドに一緒に書く)。"""
        return self._topology

    def guideSet(self):
        """このメッシュの今のガイドの組 (core.guide.guide_store から)。"""
        return guide_store.store().guideSet(self._key)

    def sync(self):
        """メッシュを読み直す。何が変わったか (UNCHANGED / MOVED / TOPOLOGY / UV) を返す。

        つながりが変わったら全部を読み直し、保存したガイドも読み直す (トポロジーが違えば使わない。Undo でトポロジーを
        戻せば、また使える)。位置が変わったら、位置とグラフ (エッジの長さ)。UV の切れ目だけなら、切れ目だけ。
        """
        face_vertices = self._mesh.faceVertices()
        if self._mesh.connectionKey(face_vertices) != self._connection_key:
            self._mesh.resetRayIndex()
            self._read_all()
            return TOPOLOGY

        uv_seams     = self._read_uv_seams(face_vertices)
        uv_changed   = not np.array_equal(uv_seams, self._uv_seams)
        self._uv_seams = uv_seams

        points       = self._mesh.points()
        world_points = self._mesh.worldPoints()
        if np.array_equal(points, self._points) and np.array_equal(world_points, self._world_points):
            return UV if uv_changed else UNCHANGED

        if not np.array_equal(points, self._points):
            self._points = points
            self._graph  = _graph(points, self._edges)
        self._world_points = world_points
        self._mirror_maps  = {}   # 反対側は位置で決めるので作り直す
        self._mesh.resetRayIndex()   # レイの索引も (動かす前の形に当たらないように)

        return MOVED

    def edges(self):
        """エッジ (M, 2) の配列。"""
        return self._edges

    def faceVertices(self):
        """面ごとの頂点の (数 (F,), 並び (角の数,)) の配列。"""
        return self._face_vertices

    def worldPoints(self):
        """頂点のワールドの位置 (N, 3) の配列。"""
        return self._world_points

    def edgeTopology(self):
        """エッジのまわりのつながり (core.path.edge_topology.EdgeTopology)。初めて使うときに作る。"""
        if self._edge_topology is None:
            counts, connects    = self._face_vertices
            self._edge_topology = EdgeTopology(self._edges, counts, connects)

        return self._edge_topology

    def mirrorMap(self, plane):
        """対称の面 (tool.symmetry.MirrorPlane) の対応表。初めて使うときに作り、見つからない頂点があればログに出す。"""
        key = (plane.space, plane.axis, plane.tolerance)
        if key not in self._mirror_maps:
            positions               = self._points if plane.space == "object" else self._world_points
            mirror                  = MirrorMap(positions, self._edges, plane.axis, plane.tolerance)
            self._mirror_maps[key]  = mirror
            unmatched               = mirror.unmatchedVertexCount()
            if unmatched:
                log.warning("{}: 反対側が見つからない頂点が {} 個あります (許容値を上げると見つかることがあります)".format(
                    self._mesh.name(), unmatched))

        return self._mirror_maps[key]

    def uvSeams(self):
        """エッジごとに UV の切れ目 (カットした所・メッシュの縁) なら True の配列 (M,)。"""
        return self._uv_seams

    def isUVSeam(self, a, b):
        """頂点 a と b を結ぶエッジが、UV の切れ目か (つながっていなければ False)。"""
        edge = self._graph.edgeBetween(a, b)

        return edge is not None and bool(self._uv_seams[edge])

    def positions(self, vertices):
        """頂点の番号の列 -> ワールドの位置 (x, y, z) のリスト。"""
        return [tuple(self._world_points[vertex]) for vertex in vertices]

    def pointPositions(self, points, world=True):
        """ガイドの点 (頂点の点) の列 -> 位置 (x, y, z) のリスト (world が False ならオブジェクト空間)。"""
        positions = self._world_points if world else self._points

        return [tuple(positions[point.vertex]) for point in points]

    def nearestVertexTo(self, position):
        """オブジェクト空間の位置にいちばん近い頂点の番号 (選んだ点をまとめて動かすとき。core.guide.group_drag)。"""
        offsets = self._points - np.asarray(position, dtype=float)

        return int(np.argmin(np.einsum("ij,ij->i", offsets, offsets)))

    def guidePositions(self, guide):
        """ガイドの線全体 (区間のシームをつないだもの) のワールドの位置のリスト。区間が無ければ点の位置。"""
        if not guide.segments:
            return self.pointPositions(guide.points)

        vertices = list(guide.segments[0].seam)
        for segment in guide.segments[1:]:
            vertices.extend(segment.seam[1:])   # 区間の境目の頂点は前の区間の最後と同じ

        return self.positions(vertices)

    # -- 非公開メソッド -------------------------------------------------------
    def _read_all(self):
        # 全部を読み直し、保存したガイドを guide_store に入れる (Undo には積まない)
        mesh = self._mesh

        self._connection_key    = mesh.connectionKey()
        self._points            = mesh.points()
        self._edges             = mesh.edgeVertices()
        self._graph             = _graph(self._points, self._edges)
        self._topology          = topology_of(len(self._points), self._edges)
        self._world_points      = mesh.worldPoints()
        self._face_vertices     = mesh.faceVertices()
        self._edge_topology     = None
        self._mirror_maps       = {}
        self._uv_seams          = self._read_uv_seams(self._face_vertices)

        guide_store.store().setGuideSet(self._key, guide_storage.load(mesh, self._topology))

    def _read_uv_seams(self, face_vertices):
        counts, connects  = face_vertices
        uv_counts, uv_ids = self._mesh.assignedUVs()

        return uv_seam_mask(self._edges, counts, connects, uv_counts, uv_ids)


def _graph(points, edges):
    # 今のまっすぐさの重みのグラフ (重みを変えたら tool_actions が今のグラフに setTurnWeight する)
    return MeshGraph(points, edges, settings.current().value("straightness"))
