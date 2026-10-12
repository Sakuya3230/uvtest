# -*- coding: utf-8 -*-
"""
輪切りの断面を、メッシュに当てる (段階 19)。

    prepared = RingTarget(model, screen)                 # 押したとき (トポロジーと画面の位置を 1 回)
    found = prepared.find(plane, stroke)                  # ドラッグのたびに (RingFound か None)
    better = prepared.refine(plane, stroke, found)        # 離したときに 1 回: なめらかに (段階 20)

なめらかにする (refine) は 2 段:
    1. 今あるループに吸い付ける: 境目のうち線の真ん中に近いエッジからループ (ダブルクリックと同じ) を
       求め、閉じていて、面に十分近い (頂点と面の距離の平均がループのエッジの平均の長さの SNAP_RATIO 倍以内)
       なら、そのループ (四角形のきれいな腕を軸に直角に近く描けば、段差の無い元のループ)
    2. だめなら core.section.smooth_ring (境目のまわりで、面に沿う道に引き直す)

切る面で分けたフェースの境目 (core.section) を使う。エッジとフェースの対応 (SectionTopology) は
MeshModel がトポロジーごとに覚えておく (MFnMesh.getVertices を 1 回)。
はじめは今あるループから選んだ (案 A) が、ドラッグのたびに Maya にループを聞くので遅く、三角形などで
一周のループが無いと見つからなかった。
"""
from ..core import accel
from ..core.section import back_half, is_closed_ring, section_edges, smooth_ring

__all__ = ["RingFound", "RingTarget", "SNAP_RATIO", "SNAP_TRIES"]

SNAP_RATIO = 0.5   # ループに吸い付ける: 頂点と面の距離の平均 <= ループのエッジの平均の長さ x これ
SNAP_TRIES = 3     # 吸い付けるループを試す数 (境目のうち、線の真ん中に近いエッジから)


class RingFound(object):
    """見つかった輪切りのエッジ。"""

    def __init__(self, edges, method="section"):
        self.edges = list(edges)   # 輪切りのエッジ
        self.method = method       # "section" (境目) / "loop" (今あるループ) / "smooth" (引き直した道)
                                   # / "seam" (縦の継ぎ目。奥側の半分。段階 21)

    def __repr__(self):
        return "RingFound({} 本, {})".format(len(self.edges), self.method)


class RingTarget(object):
    """1 つのメッシュの、ドラッグの間は変わらないもの (トポロジー・頂点の位置・画面の位置)。"""

    def __init__(self, model, screen):
        self.model = model
        self.screen_list = screen   # 頂点の画面の位置 (なめらかにするとき)
        graph = model.graph()
        self.topology = model.sectionTopology()
        modules = accel.scipy_modules()
        if modules is not None:
            np = modules[0]
            self.points = np.asarray(graph.points, dtype=np.float64)
            valid = np.fromiter((p is not None for p in screen), dtype=bool, count=len(screen))
            xy = np.asarray([p if p is not None else (0.0, 0.0) for p in screen], dtype=np.float64)
            self.screen = (valid, xy)
        else:
            self.points = graph.points
            self.screen = screen

    def find(self, plane, stroke, seam_view=None):
        """切る面 plane (点, 法線) と線 stroke で、境目のエッジ (RingFound)。無ければ None。

        seam_view (視線の向き) を渡すと縦の継ぎ目: 奥側の半分だけ (段階 21)。
        """
        edges = section_edges(self.topology, self.points, plane, self.screen, stroke)
        if seam_view is not None and edges:
            graph = self.model.graph()
            edges = back_half(graph.edges, graph.points, edges, seam_view)
            return RingFound(edges, "seam") if edges else None
        return RingFound(edges) if edges else None

    def refine(self, plane, stroke, found):
        """なめらかにした輪切り (RingFound)。吸い付ける / 引き直す ができなければ found のまま。"""
        if found is None or plane is None:
            return found
        loop = self._snap(plane, stroke, found.edges)
        if loop is not None:
            return RingFound(loop, "loop")
        smooth = smooth_ring(self.model.graph(), plane, found.edges, self.screen_list, stroke)
        if smooth is not None:
            return RingFound(smooth, "smooth")
        return found

    def _snap(self, plane, stroke, edges):
        """境目の近くの、今あるループ (閉じていて面に近い)。無ければ None。"""
        graph = self.model.graph()
        origin, normal = plane
        screen = self.screen_list

        def middle_distance(edge):
            a, b = graph.edges[edge]
            if screen[a] is None or screen[b] is None:
                return float("inf")
            t, d = stroke.project(((screen[a][0] + screen[b][0]) * 0.5, (screen[a][1] + screen[b][1]) * 0.5))
            return abs(t - 0.5) * stroke.length + d

        tried = set()   # 試したループのエッジ
        loops = 0
        for edge in sorted(edges, key=middle_distance):
            if loops >= SNAP_TRIES:
                break
            if edge in tried:
                continue
            loop = self.model.edgeLoop(edge)
            tried.update(loop)
            loops += 1
            if not is_closed_ring(graph.edges, loop):
                continue
            vertices = set(v for e in loop for v in graph.edges[e])
            mean_distance = sum(abs(sum((graph.points[v][k] - origin[k]) * normal[k] for k in range(3)))
                                for v in vertices) / len(vertices)
            mean_length = sum(graph.lengths[e] for e in loop) / len(loop)
            if mean_distance <= mean_length * SNAP_RATIO:
                return loop
        return None
