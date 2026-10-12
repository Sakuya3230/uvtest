# -*- coding: utf-8 -*-
"""
ツールを使っている間の、パスの状態 (Maya に依存しない)。

段階 7:
    session = PathSession(graph)
    session.setStart(Waypoint("edge", 12))       # スタートを決めたときに 1 回だけ探す (PathTree)
    path = session.pathTo(Waypoint("vertex", 3))  # ホバーのたび (たどるだけ)
    session.clearStart()                          # Esc

スタートを決めたときに core.path.path_tree で探しておき (scipy なら全頂点まで 1 回)、ホバーでは
その木から道をたどるだけにする。スタートが変わらない限り、何度ホバーしても探し直さない。
段階 8:
    session.push(PathSegment(...)) / session.pop()   確定した区間のスタック (scene.edit のコマンドだけが呼ぶ)
    session.addListener(fn)                          変わったら (notify) 知らせる
段階 9:
    segment.operation                                実行した操作 (カット / 縫合 / まだなら None)
    session.pendingSegments()                        まだ実行していない区間
段階 15:
    PathSession(graph, turn_weight=1.0)              曲がりの重み (core.turning)。0 なら長さだけ
    session.setTurnWeight(w)                         重みを替える (スタートがあれば探し直す)
段階 13:
    session.setGraph(graph)                          頂点の位置が変わったグラフに入れ替える
                                                     (スタートからの PathTree を作り直し、区間の長さを測り直す)
"""
from .path import Waypoint, path_tree
from .picking import PICK_VERTEX

__all__ = ["PathSession", "PathSegment", "waypoint_of", "waypoint_label", "preview_label",
           "OPERATION_CUT", "OPERATION_SEW", "OPERATION_LABELS"]

# UV の操作 (設定 operation の選択肢と同じ名前。段階 9)
OPERATION_CUT = "cut"    # UV を切る (polyMapCut)
OPERATION_SEW = "sew"    # UV を縫い合わせる (polyMapSew)
OPERATION_LABELS = {OPERATION_CUT: "カット", OPERATION_SEW: "縫合"}


def waypoint_of(pick):
    """拾ったもの (core.picking.Pick) の端点 (Waypoint)。"""
    return Waypoint(pick.kind, pick.index)


def waypoint_label(waypoint):
    """端点の名前 (vtx[3] / e[12])。"""
    return "{}[{}]".format("vtx" if waypoint.kind == PICK_VERTEX else "e", waypoint.index)


def preview_label(pick, path, has_start):
    """エンドの候補 (マウスの下) に添える文字。

    スタートが無ければ番号だけ。あれば、パスのエッジの本数と長さ (つながっていなければそう書く)。
    """
    label = pick.label()
    if not has_start:
        return label
    if path is None:
        return label + "  (つながっていない)"
    if path.edges:
        return "{}  {} 本 / 長さ {:.3f}".format(label, len(path.edges), path.length)
    return label   # スタートと同じもの


class PathSegment(object):
    """確定した 1 区間 (スタートからエンドまで。段階 8)。"""

    def __init__(self, start, end, path):
        self.start = start            # Waypoint
        self.end = end                # Waypoint
        self.edges = list(path.edges)
        self.vertices = list(path.vertices)
        self.length = path.length
        self.operation = None   # 実行した操作 (OPERATION_CUT / OPERATION_SEW)。まだなら None (段階 9)
        self.mirror_edges = []  # 反対側のエッジ (対称がオンで確定したとき。段階 17)
        self.mirror_missing = 0  # 反対側が見つからなかったエッジの数

    def setMirror(self, mirror):
        """反対側のエッジを対応表 (core.mirror.MirrorMap) から決める (確定するとき。段階 17)。

        確定したときに決めて区間が持つので、あとで対称をオフにしても、この区間は両側のまま
        (Undo / Redo でも同じ)。自分と同じエッジ (面の上のエッジ) は足さない。
        """
        if mirror is None:
            self.mirror_edges, self.mirror_missing = [], 0
            return
        own = set(self.edges)
        mirrored, self.mirror_missing = mirror.edges(self.edges)
        result = []
        for edge in mirrored:
            if edge not in own:
                own.add(edge)
                result.append(edge)
        self.mirror_edges = result

    def allEdges(self):
        """この区間で選択する (段階 9 からはカット / 縫合する) エッジ。対称なら反対側も (段階 17)。"""
        return list(self.edges) + list(self.mirror_edges)

    def __repr__(self):
        mirror = " + 反対側 {} 本".format(len(self.mirror_edges)) if self.mirror_edges else ""
        return "PathSegment({} -> {}, {} 本{}, {})".format(
            waypoint_label(self.start), waypoint_label(self.end), len(self.edges), mirror,
            OPERATION_LABELS.get(self.operation, "未実行"))


class PathSession(object):
    """ツールを使っている間の、パスの状態。

    未確定のスタートと、確定した区間のスタック (segments) を持つ。区間を積む / 戻すのは
    Undo できるコマンド (scene.edit) だけ。変わったら notify() でリスナーに知らせる
    (コンテキストが表示を更新する。Undo / Redo で変わったときも同じ経路)。

    tree_factory(graph, start) -> PathTree は、テストで探し方を替えるためのもの
    (省けば core.path.path_tree。scipy があれば scipy、無ければ Python)。
    """

    def __init__(self, graph, tree_factory=None, turn_weight=0.0):
        self.graph = graph
        self.start = None    # 未確定のスタート (Waypoint)。無ければ None
        self.segments = []   # 確定した区間 (PathSegment) のスタック (段階 8)
        self.turn_weight = turn_weight   # 曲がりの重み (段階 15。tree_factory を渡したときは使わない)
        self._tree = None    # スタートからの PathTree
        self._tree_factory = tree_factory
        self._listeners = []

    def _make_tree(self, start):
        if self._tree_factory is not None:
            return self._tree_factory(self.graph, start)
        return path_tree(self.graph, start, turn_weight=self.turn_weight)

    def setTurnWeight(self, weight):
        """曲がりの重みを替える (段階 15)。スタートがあれば、新しい重みで探し直す。"""
        if weight == self.turn_weight:
            return
        self.turn_weight = weight
        if self.start is not None:
            self._tree = self._make_tree(self.start)

    # -- 区間のスタック (段階 8) ---------------------------------------------------

    def push(self, segment):
        self.segments.append(segment)

    def pop(self):
        return self.segments.pop()

    def edges(self, segments=None):
        """区間 (省けば確定した区間すべて) のエッジ (重複なし、確定した順)。"""
        seen = set()
        result = []
        for segment in self.segments if segments is None else segments:
            for edge in segment.allEdges():
                if edge not in seen:
                    seen.add(edge)
                    result.append(edge)
        return result

    def pendingSegments(self):
        """まだカット / 縫合していない区間 (段階 9)。"""
        return [segment for segment in self.segments if segment.operation is None]

    # -- 変更の通知 ----------------------------------------------------------------

    def addListener(self, listener):
        """listener(session) を、セッションが変わったとき (notify) に呼ぶ。"""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def removeListener(self, listener):
        if listener in self._listeners:
            self._listeners.remove(listener)

    def notify(self):
        for listener in list(self._listeners):
            listener(self)

    def setGraph(self, graph):
        """グラフを入れ替える (頂点の位置が変わったとき。トポロジーは同じであること。段階 13)。

        区間はエッジの番号で持っているのでそのまま使える (描くときに新しい位置を読む)。
        長さは位置で変わるので測り直す。スタートがあれば、新しい位置で PathTree を作り直す。
        """
        self.graph = graph
        for segment in self.segments:
            segment.length = sum(graph.lengths[e] for e in segment.edges)
        if self.start is not None:
            self._tree = self._make_tree(self.start)

    def setStart(self, waypoint):
        """スタートを決め、そこからの PathTree を作る (同じスタートなら作り直さない)。"""
        if waypoint is None:
            self.clearStart()
            return
        if self._tree is None or self._tree.start != waypoint:
            self._tree = self._make_tree(waypoint)
        self.start = waypoint

    def clearStart(self):
        self.start = None
        self._tree = None

    def tree(self):
        return self._tree

    def pathTo(self, goal):
        """スタートから goal までのパス。スタートが無い・つながっていなければ None。"""
        if self.start is None:
            return None
        return self._tree.pathTo(goal)
