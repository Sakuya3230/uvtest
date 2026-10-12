# -*- coding: utf-8 -*-
"""
対象のメッシュの集まり (段階 14。複数のメッシュ)。

    targets = TargetSet(session_factory)    # session_factory(graph) -> PathSession
    added, removed = targets.setShapes(shapes)   # 今の対象 (シェイプのフルパスのリスト) に合わせる
    added = targets.add(shapes)                  # 対象に加える (外さない)
    target, hit = targets.hit(source, direction) # レイがいちばん手前で当たるメッシュと面
    target.session(create=True)                  # そのメッシュの今のセッション (初めてなら作る)
    targets.sync()                               # 外部の変更を取り込む [(target, kind, status)]
    pairs, ignored = targets.selectedEdges()     # 選んでいるエッジ [(target, edges)] (段階 16)
    targets.release()                            # コールバックを外す

仕組み:
- メッシュ 1 つの状態 (MeshTarget) = MeshModel (面・グラフ・外部の変更) + SessionBook
  (トポロジーごとのセッション。段階 13)。段階 13 までコンテキストが 1 つずつ持っていたものを、
  メッシュごとにまとめた
- 見分けは MObjectHandle (Maya を起動している間の同じノード。名前を変えても同じ)。対象から外れた
  メッシュも覚えておき (known)、また対象になったら前の区間のまま使う (Undo で選択が戻ったときなど)
- グラフ (と SessionBook) は、そのメッシュを初めてクリックしたときに作る (session(create=True))。
  ホバー (面に当てて頂点 / エッジを拾う) にはグラフが要らないので、対象が多くても最初は軽い
- ホバーは対象すべてにレイを当て、始点にいちばん近い交点のメッシュを使う
"""
import maya.api.OpenMaya as om

from ..core.sync import CHANGE_NONE, SessionBook
from .mesh import MeshModel, dag_path
from .mirror import cached_mirror_map

__all__ = ["MeshTarget", "TargetSet"]


def _distance2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


class MeshTarget(object):
    """対象のメッシュ 1 つ (MeshModel と、トポロジーごとのセッション)。"""

    def __init__(self, shape, session_factory):
        self.model = MeshModel(shape)
        self.handle = om.MObjectHandle(self.model.path.node())
        self._factory = session_factory
        self.book = None   # core.sync.SessionBook (初めてクリックしたときに作る)

    def __repr__(self):
        return "MeshTarget({})".format(self.name() if self.isValid() else "(消えた)")

    def name(self):
        """シェイプの今のフルパス。"""
        return self.model.name()

    def isValid(self):
        return self.model.isValid()

    def matches(self, node):
        """node (MObject) がこのメッシュか。"""
        return self.handle == om.MObjectHandle(node)

    def session(self, create=False):
        """今のトポロジーのセッション。まだ無ければ None (create=True なら、グラフを作って作る)。"""
        if self.book is None:
            if not create:
                return None
            self.book = SessionBook(self._factory)
            self.book.sessionFor(self.model.topologyKey(), self.model.graph())
        return self.book.current

    def sessions(self):
        """覚えているセッションすべて (トポロジーごと)。"""
        return self.book.sessions() if self.book is not None else []

    def sync(self):
        """外部の変更を取り込む。(変更の種類, セッションの状態) (段階 13 と同じ判定)。"""
        kind = self.model.sync()
        if kind == CHANGE_NONE or self.book is None:
            return kind, None
        _session, status = self.book.sessionFor(self.model.topologyKey(), self.model.graph())
        return kind, status

    def mirror(self, plane, build=True):
        """対称の面 plane の対応表 (scene.mirror.cached_mirror_map。段階 17)。(対応表, 覚えていたか)。

        グラフ (MeshModel.graph) が要るので、まだ作っていなければここで作る。
        """
        return cached_mirror_map(self.model, plane, build)

    def release(self):
        self.model.release()


class TargetSet(object):
    """対象のメッシュの集まり。active が今の対象、known は一度でも対象にしたもの。"""

    def __init__(self, session_factory):
        self._factory = session_factory
        self.known = []    # [MeshTarget] (外れても覚えておく)
        self.active = []   # [MeshTarget] (今の対象。setShapes の順)

    def __len__(self):
        return len(self.active)

    def __iter__(self):
        return iter(self.active)

    def find(self, node):
        """node (MObject) の MeshTarget (覚えていなければ None)。"""
        for target in self.known:
            if target.isValid() and target.matches(node):
                return target
        return None

    def setShapes(self, shapes):
        """今の対象をシェイプ (フルパス) のリストに合わせる。(増えた, 外れた) の MeshTarget のリスト。

        並びは、前からの対象は前の順のまま、増えたものを後ろに足す (選択の順で入れ替わらない)。
        """
        before = list(self.active)
        active = []
        for shape in shapes:
            node = dag_path(shape).node()
            target = self.find(node)
            if target is None:
                target = MeshTarget(shape, self._factory)
                self.known.append(target)
            if target not in active:
                active.append(target)
        # 並びは安定させる (前からの対象は前の順のまま、新しいものを後ろに)
        active = [t for t in before if t in active] + [t for t in active if t not in before]
        self.active = active
        added = [t for t in active if t not in before]
        removed = [t for t in before if t not in active]
        return added, removed

    def add(self, shapes):
        """シェイプ (フルパス) を対象に加える (今の対象は外さない)。増えた MeshTarget のリスト。

        消えたメッシュも active に残す (valid() が飛ばす。Undo で戻れば、また対象として使う)。
        """
        before = list(self.active)
        names = [t.name() for t in before if t.isValid()]
        self.setShapes(names + [s for s in shapes if s not in names])
        self.active = before + [t for t in self.active if t not in before]
        return [t for t in self.active if t not in before]

    def valid(self):
        """今の対象のうち、シーンにあるもの。"""
        return [t for t in self.active if t.isValid()]

    def sessions(self):
        """[(MeshTarget, 今のセッション)] (セッションのある、今の対象だけ)。"""
        result = []
        for target in self.valid():
            session = target.session()
            if session is not None:
                result.append((target, session))
        return result

    def owner(self, session):
        """session を持つ MeshTarget (覚えているものから。無ければ None)。"""
        for target in self.known:
            if session in target.sessions():
                return target
        return None

    def hit(self, source, direction, front_only=True):
        """レイがいちばん手前で当たる (MeshTarget, core.picking.FaceHit)。当たらなければ (None, None)。"""
        best = (None, None)
        best_distance = None
        origin = tuple(source)[:3]
        for target in self.valid():
            hit = target.model.hit(source, direction, front_only)
            if hit is None:
                continue
            distance = _distance2(origin, hit.point)
            if best_distance is None or distance < best_distance:
                best, best_distance = (target, hit), distance
        return best

    def selectedEdges(self, selection=None):
        """選んでいる、今の対象のメッシュのエッジ。([(MeshTarget, [エッジ])], エッジ以外を選んでいたか)。

        selection (MSelectionList) を省くと今の選択。対象でないメッシュのエッジは数えない。
        頂点・面などエッジ以外のコンポーネントは使わず、ignored を True にする (オブジェクトとして
        選んでいるだけのものは数えない)。メッシュの並びは対象の順。
        """
        if selection is None:
            selection = om.MGlobal.getActiveSelectionList()
        found = {}
        ignored = False
        for index in range(selection.length()):
            try:
                path, component = selection.getComponent(index)
            except (RuntimeError, TypeError):
                continue   # DAG でないもの (ノードなど)
            if component.isNull():
                continue
            if component.apiType() != om.MFn.kMeshEdgeComponent:
                ignored = True
                continue
            try:
                path.extendToShape()   # Transform の名前で選んでいてもシェイプに
            except RuntimeError:
                pass
            target = self.find(path.node())
            if target is None or target not in self.active:
                continue
            edges = om.MFnSingleIndexedComponent(component).getElements()
            found.setdefault(target, set()).update(edges)
        pairs = [(target, sorted(found[target])) for target in self.active if target in found]
        return pairs, ignored

    def sync(self):
        """今の対象の外部の変更を取り込む。変わったものの [(MeshTarget, 種類, セッションの状態)]。"""
        changes = []
        for target in self.valid():
            kind, status = target.sync()
            if kind != CHANGE_NONE:
                changes.append((target, kind, status))
        return changes

    def release(self):
        for target in self.known:
            target.release()
        self.known = []
        self.active = []
