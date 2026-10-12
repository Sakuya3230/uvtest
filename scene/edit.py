# -*- coding: utf-8 -*-
"""
シーンを変える操作と Undo。

段階 8: 確定
    segment = confirm_path(session, shape, goal)   # 1 回の Undo で、区間を積み・スタートを進め・選択を変える
段階 9: カット / 縫合
    confirm_path(session, shape, goal, "cut")      # 自動カット: 確定と同じ Undo の中でカット
    apply_pending(session, shape, "sew")           # ためた区間をまとめて縫合 (1 回の Undo)
段階 10: リセット
    clear_session(session)                         # 区間・スタート・選択をすべて外す (1 回の Undo)
段階 14: 複数のメッシュ
    confirm_path(..., others=[(shape, edges)])     # ほかのメッシュの区間のエッジも選んだままにする
    apply_pending_all([(session, shape)], "cut")   # 全メッシュのためた区間を 1 回の Undo で
    clear_sessions([session, ...])                 # 全メッシュの区間を 1 回の Undo で外す
段階 19: 輪切り
    confirm_ring(session, shape, edges, "cut")     # 輪切りのループを区間として積む (パスのスタートは変えない)
段階 16: 選択のモード
    apply_selection([(shape, edges, session)], "cut")   # 選んでいるエッジをカット / 縫合 (1 回の Undo)

仕組み:
- 変更 (Change) は redo() / undo() を持つ小さなオブジェクト。1 回の Undo で行う変更をリストにして、
  Undo できるコマンド uvPathCutEdit (PathEditCommand) に渡す。コマンドは doIt / redoIt で順に redo し、
  undoIt で逆の順に undo する。途中で失敗したら、行った分を戻してから例外を投げる
- コマンドには Python のオブジェクトを引数で渡せないので、_PENDING (このモジュールの変数) に
  置いてから呼ぶ (ウェイトスライダー・旧版と同じ)
- Undo の記録の名前は「実行した MEL の文字列」。Python の cmds で呼ぶと空になる (ウェイトスライダーで
  確認) ので、MEL で uvPathCutEdit -n "<名前>" と呼ぶ。-n の中身は名前のためだけ
- MGlobal.setActiveSelectionList は、それ自身では Undo に載らない。変える前の選択を覚えておき、
  undo で戻す (SelectionChange)
- 選択の変更 (SelectionChange) は、コマンドがいつも最後に行う (redo でも undo でも)。
  polyMapCut / polyMapSew は、エッジを選んでいると「対象のエッジ」を選択にしてしまう
  (自動カットで 2 区間目を確定すると、全区間ではなく 2 区間目のエッジだけが選ばれていた)。
  最後に選択を決め直せば、途中で変わっても正しい選択になる
- コマンドは変えたセッションを持つ。Undo / Redo のあとは session.notify() でリスナー (使っている
  ツールのコンテキスト) に知らせる。ツールを抜けたあとの Undo では、表示されていないセッションを
  変えるだけで、選択だけが目に見えて戻る。コマンドは表示 (tool) のことを知らない
- プラグインはこのクラスを直接登録しない。creator が毎回このモジュールを引く
- UV を変えるのは polyMapCut / polyMapSew。MDGModifier.commandToExecute で実行し、modifier の
  undoIt で戻す (UVChange)。Undo でノード (polyMapCut など) が消え、ヒストリーの無いメッシュも
  元に戻り、もう一度 doIt すればやり直せる。エッジを選んでいると、対象のエッジを選択にする
  (上の SelectionChange で決め直す)
"""
import maya.api.OpenMaya as om
import maya.mel as mel

from ..constants import EDIT_COMMAND
from ..core.components import edge_component_names
from ..core.mirror import with_mirror
from ..core.path import PathResult, Waypoint
from ..core.picking import PICK_EDGE
from ..core.session import OPERATION_CUT, OPERATION_LABELS, OPERATION_SEW, PathSegment
from .mesh import dag_path

__all__ = ["apply_selection", "covered_segments", "ConfirmChange", "SelectionChange", "UVChange", "OperationChange", "ResetChange",
           "PathEditCommand", "run_changes", "confirm_path", "confirm_ring", "apply_pending", "apply_pending_all",
           "clear_session", "clear_sessions", "edge_selection", "edges_selection"]

# 操作 -> MEL のコマンド
OPERATION_COMMANDS = {OPERATION_CUT: "polyMapCut", OPERATION_SEW: "polyMapSew"}

_PENDING = []   # コマンドに渡す (セッション, 変更のリスト)。コマンドの引数では Python のオブジェクトを渡せない


def edge_selection(shape, edges):
    """shape のエッジ edges だけを入れた MSelectionList (edges が空なら空の選択)。"""
    selection = om.MSelectionList()
    if edges:
        component = om.MFnSingleIndexedComponent()
        obj = component.create(om.MFn.kMeshEdgeComponent)
        component.addElements(list(edges))
        selection.add((dag_path(shape), obj))
    return selection


def edges_selection(pairs):
    """[(shape, edges)] (メッシュごとのエッジ) を 1 つにした MSelectionList (段階 14)。"""
    selection = om.MSelectionList()
    for shape, edges in pairs:
        if edges:
            selection.merge(edge_selection(shape, edges))
    return selection


class ConfirmChange(object):
    """1 回の確定で変わるもの: スタックに積む区間とスタート (選択は SelectionChange)。"""

    def __init__(self, session, segment, start_before, start_after):
        self.session = session
        self.segment = segment
        self.start_before = start_before
        self.start_after = start_after

    def redo(self):
        self.session.push(self.segment)
        self.session.setStart(self.start_after)

    def undo(self):
        self.session.pop()
        self.session.setStart(self.start_before)


class SelectionChange(object):
    """選択を変える (前後の MSelectionList を覚える)。

    final = True の変更は、コマンドがいつも最後に行う (redo でも undo でも)。ほかの変更
    (polyMapCut など) が途中で選択を変えても、最後に決め直すため。
    """

    final = True

    def __init__(self, before, after):
        self.before = before
        self.after = after

    def redo(self):
        om.MGlobal.setActiveSelectionList(self.after)

    def undo(self):
        om.MGlobal.setActiveSelectionList(self.before)


class UVChange(object):
    """エッジの UV をカット / 縫合する (段階 9)。

    MDGModifier.commandToExecute(MEL の文字列) は「doIt で実行し、undoIt で取り消す」操作を
    modifier に足す。MEL のコマンドが Undo できる (polyMapCut / polyMapSew はできる) ことが条件。
    コマンドの文字列は作ったときに決める (エッジは範囲にまとめる)。
    """

    def __init__(self, shape, edges, operation):
        components = " ".join('"{}"'.format(name) for name in edge_component_names(shape, edges))
        self.command = "{} {}".format(OPERATION_COMMANDS[operation], components)
        self.modifier = om.MDGModifier()
        self.modifier.commandToExecute(self.command)

    def redo(self):
        self.modifier.doIt()

    def undo(self):
        self.modifier.undoIt()


class OperationChange(object):
    """区間に、実行した操作の印を付ける (表示の色と、まとめて実行の対象から外すため。段階 9)。"""

    def __init__(self, segments, operation):
        self.segments = list(segments)
        self.before = [segment.operation for segment in self.segments]
        self.operation = operation

    def redo(self):
        for segment in self.segments:
            segment.operation = self.operation

    def undo(self):
        for segment, operation in zip(self.segments, self.before):
            segment.operation = operation


class ResetChange(object):
    """確定した区間とスタートをすべて外す (段階 10)。undo で元の区間とスタートに戻す。

    区間のスタックは Undo できるコマンドだけが積み下ろしするので、リセットも Undo に載せる。
    載せずに空にすると、そのあとの Ctrl+Z (確定の undo) が空のスタックから取り出そうとして壊れる。
    UV のカット / 縫合は戻さない (ツールの記録だけを外す)。
    """

    def __init__(self, session):
        self.session = session
        self.segments = list(session.segments)
        self.start = session.start

    def redo(self):
        del self.session.segments[:]
        self.session.clearStart()

    def undo(self):
        self.session.segments[:] = self.segments
        self.session.setStart(self.start)


class PathEditCommand(om.MPxCommand):
    """uvPathCutEdit: 変更のリストを 1 回の Undo として行うコマンド (run_changes から呼ぶ)。"""

    def __init__(self):
        super().__init__()
        self._sessions = []   # 変えたセッション (段階 14 から複数のことがある)
        self._changes = []

    @staticmethod
    def syntax():
        # -n (名前): Undo の記録の名前にするためだけの引数 (中身は使わない)
        syntax = om.MSyntax()
        syntax.addFlag("-n", "-name", om.MSyntax.kString)
        return syntax

    def isUndoable(self):
        # True を返すと、このコマンドが Undo のキューに積まれる
        return True

    def doIt(self, args):
        if not _PENDING:
            raise RuntimeError("{} はツールから呼ばれるコマンドです".format(EDIT_COMMAND))
        sessions, self._changes = _PENDING.pop()
        self._sessions = sessions if isinstance(sessions, (list, tuple)) else [sessions]
        del _PENDING[:]
        self.redoIt()

    def _ordered(self):
        """(ふつうの変更, 最後に行う変更 (final。選択)) に分ける。"""
        normal = [c for c in self._changes if not getattr(c, "final", False)]
        final = [c for c in self._changes if getattr(c, "final", False)]
        return normal, final

    def redoIt(self):
        normal, final = self._ordered()
        done = []
        try:
            for change in normal + final:   # 選択 (final) はいつも最後
                change.redo()
                done.append(change)
        except Exception:
            for change in reversed(done):   # 途中で失敗したら、行った分を戻してから投げる
                change.undo()
            raise
        self._notify()

    def undoIt(self):
        normal, final = self._ordered()
        for change in list(reversed(normal)) + final:   # 選択 (final) は undo でも最後に戻す
            change.undo()
        self._notify()

    def _notify(self):
        for session in self._sessions:
            session.notify()


def run_changes(session, changes, label):
    """変更のリストを 1 回の Undo として行う (MEL で uvPathCutEdit -n "<label>")。

    session は変えるセッション (段階 14 からはリストでもよい)。行ったあと・戻したあとに知らせる。
    """
    _PENDING[:] = [(session, changes)]
    text = label.replace("\\", "/").replace('"', "'")   # MEL の文字列に入れられない文字を避ける
    try:
        mel.eval('{} -n "{}"'.format(EDIT_COMMAND, text))
    finally:
        del _PENDING[:]


def confirm_path(session, shape, goal, operation=None, others=(), mirror=None):
    """スタートから goal までを確定する (1 回の Undo)。確定した PathSegment か None。

    区間をスタックに積み、goal を次のスタートにし、確定した区間すべてのエッジを選ぶ。
    operation ("cut" / "sew") を渡すと (自動カット)、同じ Undo の中でその区間をカット / 縫合する。
    others ([(シェイプ, エッジ)]) は、ほかのメッシュの区間のエッジ (一緒に選んだままにする。段階 14)。
    mirror (core.mirror.MirrorMap。対称がオンのとき) を渡すと、区間に反対側のエッジも持たせ、
    選択・カット / 縫合を両側で行う (同じ Undo。段階 17)。
    スタートが無い・goal がスタートと同じ・つながっていなければ None (何もしない)。
    """
    if session.start is None or goal == session.start:
        return None
    path = session.pathTo(goal)
    if path is None:
        return None
    segment = PathSegment(session.start, goal, path)
    _push_segment(session, shape, segment, goal, operation, others, mirror, "UV パスの確定")
    return segment


def confirm_ring(session, shape, edges, operation=None, others=(), mirror=None, title="UV 輪切りの確定"):
    """輪切りのループを確定する (1 回の Undo。段階 19)。確定した PathSegment か None。

    パスの区間と同じくスタックに積んで「ためる」(自動カットなら同じ Undo でカット / 縫合)。
    パスのスタートは変えない。区間の両端は、ループの最初のエッジ (印を 1 つ付けるため)。
    """
    edges = list(edges)
    if not edges:
        return None
    graph = session.graph
    vertices = []
    for edge in edges:
        for vertex in graph.edges[edge]:
            if vertex not in vertices:
                vertices.append(vertex)
    path = PathResult(vertices, edges, sum(graph.lengths[e] for e in edges))
    mark = Waypoint(PICK_EDGE, edges[0])
    segment = PathSegment(mark, mark, path)
    _push_segment(session, shape, segment, session.start, operation, others, mirror, title)
    return segment


def _push_segment(session, shape, segment, start_after, operation, others, mirror, title):
    """区間を積み、スタートを start_after にし、全区間のエッジを選ぶ (自動カットなら実行も)。1 回の Undo。"""
    segment.setMirror(mirror)
    existing = session.edges()
    known = set(existing)
    edges_after = existing + [e for e in segment.allEdges() if e not in known]
    changes = [ConfirmChange(session, segment, session.start, start_after),
               SelectionChange(om.MGlobal.getActiveSelectionList(),
                               edges_selection(list(others) + [(shape, edges_after)]))]
    count = len(segment.allEdges())
    both = " 両側" if segment.mirror_edges else ""
    label = "{} ({} 本{})".format(title, count, both)
    if operation is not None and segment.edges:
        changes.append(UVChange(shape, segment.allEdges(), operation))
        changes.append(OperationChange([segment], operation))
        label = "{}と{} ({} 本{})".format(title, OPERATION_LABELS[operation], count, both)
    run_changes(session, changes, label)


def apply_pending(session, shape, operation):
    """まだ実行していない区間をまとめてカット / 縫合する (1 回の Undo)。対象の区間のリスト。

    無ければ何もせず [] を返す。実行した区間には印 (operation) を付け、次からは対象にしない。
    """
    return apply_pending_all([(session, shape)], operation)


def apply_pending_all(pairs, operation):
    """[(セッション, シェイプ)] のまだ実行していない区間を、まとめて 1 回の Undo で実行する (段階 14)。

    メッシュごとに UVChange を 1 つ作る (polyMapCut はメッシュごとのノード)。対象の区間のリスト。
    """
    changes = []
    sessions = []
    all_segments = []
    edge_count = 0
    for session, shape in pairs:
        segments = session.pendingSegments()
        edges = session.edges(segments)
        if not edges:
            continue
        changes.append(UVChange(shape, edges, operation))
        changes.append(OperationChange(segments, operation))
        sessions.append(session)
        all_segments.extend(segments)
        edge_count += len(edges)
    if not changes:
        return []
    label = "UV パスの{} ({} 区間 / {} 本".format(OPERATION_LABELS[operation], len(all_segments),
                                               edge_count)
    label += " / {} メッシュ)".format(len(sessions)) if len(sessions) > 1 else ")"
    # 選択は実行の前のまま (polyMapCut が対象のエッジだけを選ぶので、前の選択に決め直す)
    selection = om.MGlobal.getActiveSelectionList()
    changes.append(SelectionChange(selection, selection))
    run_changes(sessions, changes, label)
    return all_segments


def covered_segments(session, edges):
    """まだ実行していない区間のうち、エッジがすべて edges に入っているもの (段階 16)。

    選んだエッジでカット / 縫合したとき、その区間も実行したことになるので印を付ける
    (付けないと、カットしたのに「未実行」の色のまま残り、まとめて実行の対象にもなる)。
    一部だけ入っている区間には付けない (残りのエッジはまだ実行していない)。
    """
    chosen = set(edges)
    return [segment for segment in session.pendingSegments()
            if segment.allEdges() and chosen.issuperset(segment.allEdges())]


def apply_selection(items, operation, mirrors=None):
    """選んでいるエッジを、メッシュごとにカット / 縫合する (全部で 1 回の Undo。段階 16)。

    items は [(シェイプ, エッジのリスト, セッションか None)]。エッジの無いメッシュは飛ばす。
    mirrors ({シェイプ: core.mirror.MirrorMap}。対称がオンのとき。段階 17) があれば、そのメッシュは
    選んだエッジに反対側を足して実行する (覆われた区間も、足したエッジで決める)。
    セッションがあれば、エッジで覆われた未実行の区間に印を付ける (covered_segments)。
    選択は実行の前のまま (polyMapCut がエッジを選び直すので、最後に決め直す)。
    戻り値は (実行したエッジの数, 印を付けた区間の数)。何もしなければ (0, 0)。
    """
    changes = []
    sessions = []
    edge_count = 0
    marked = 0
    meshes = 0
    for shape, edges, session in items:
        mirror = (mirrors or {}).get(shape)
        edges = sorted(with_mirror(edges, mirror)[0])
        if not edges:
            continue
        changes.append(UVChange(shape, edges, operation))
        edge_count += len(edges)
        meshes += 1
        if session is not None:
            covered = covered_segments(session, edges)
            if covered:
                changes.append(OperationChange(covered, operation))
                marked += len(covered)
            sessions.append(session)   # Undo / Redo で表示を直すため (印が無くても知らせる)
    if not changes:
        return 0, 0
    label = "UV 選択の{} ({} 本".format(OPERATION_LABELS[operation], edge_count)
    label += " / {} メッシュ)".format(meshes) if meshes > 1 else ")"
    selection = om.MGlobal.getActiveSelectionList()
    changes.append(SelectionChange(selection, selection))
    run_changes(sessions, changes, label)
    return edge_count, marked


def clear_session(session):
    """確定した区間・スタート・エッジの選択をすべて外す (1 回の Undo。段階 10)。

    外したものが無ければ何もせず None。外したら (区間の数, まだ実行していなかった区間の数)。
    """
    return clear_sessions([session])


def clear_sessions(sessions):
    """複数のセッション (メッシュごと) の区間・スタートと選択を、1 回の Undo で外す (段階 14)。"""
    sessions = [s for s in sessions if s.segments or s.start is not None]
    if not sessions:
        return None
    counts = (sum(len(s.segments) for s in sessions),
              sum(len(s.pendingSegments()) for s in sessions))
    changes = [ResetChange(session) for session in sessions]
    changes.append(SelectionChange(om.MGlobal.getActiveSelectionList(), om.MSelectionList()))
    run_changes(sessions, changes, "UV パスのクリア ({} 区間)".format(counts[0]))
    return counts
