# -*- coding: utf-8 -*-
"""
外部の変更の判定と、トポロジーごとのセッション (Maya に依存しない。段階 13)。

    key = topology_key(counts, connects)            # 面ごとの頂点の数と並び (MFnMesh.getVertices)
    kind = classify(old_key, new_key, old_points, new_points)
        CHANGE_NONE      何も変わっていない (自分の UV のカット / 縫合など)
        CHANGE_POINTS    頂点の位置だけ変わった (変形・移動。エッジの番号はそのまま使える)
        CHANGE_TOPOLOGY  頂点・面のつながりが変わった (エッジの番号が別のものを指す)

    book = SessionBook(PathSession)
    session, status = book.sessionFor(key, graph)   # そのトポロジーのセッション
        STATUS_SAME      今のセッションのまま (位置だけ変わったなら graph を入れ替えた)
        STATUS_NEW       初めてのトポロジー。新しいセッション
        STATUS_RESTORED  前に使ったトポロジーに戻った。そのときのセッション (区間) に戻す

旧版との違い:
- 旧版は「自分のカット / 縫合の間は通知を無視する」印 (writing) を立てていた。今の版は、通知では
  「変わったかも」という印だけを付け、使うときに中身 (トポロジーの鍵と頂点の位置) を比べる。
  自分の UV の変更は中身が変わらないので CHANGE_NONE になり、特別扱いが要らない
- 旧版はトポロジーが変わるとセッションを作り直して区間を捨てていた。今の版はトポロジーの鍵ごとに
  セッションを覚えておく。確定のコマンドは自分のセッションを持っているので、Undo でトポロジーが
  元に戻れば、元のセッション (と、その Undo の続き) がそのまま使える
"""
__all__ = ["CHANGE_NONE", "CHANGE_POINTS", "CHANGE_TOPOLOGY", "STATUS_SAME", "STATUS_NEW",
           "STATUS_RESTORED", "topology_key", "classify", "SessionBook"]

CHANGE_NONE = "none"
CHANGE_POINTS = "points"
CHANGE_TOPOLOGY = "topology"

STATUS_SAME = "same"
STATUS_NEW = "new"
STATUS_RESTORED = "restored"


def topology_key(counts, connects, vertex_count=None):
    """トポロジーの鍵 (同じなら、頂点・エッジの番号が同じものを指すとみなす)。

    counts は面ごとの頂点の数、connects は面ごとの頂点の番号を並べたもの (MFnMesh.getVertices)。
    エッジの番号は面と頂点の並びから決まるので、これが同じならエッジの番号も同じ。
    全部を持つと大きいので、数と hash にする (hash は同じプロセスの中でだけ比べる)。
    """
    counts = tuple(counts)
    connects = tuple(connects)
    vertices = vertex_count if vertex_count is not None else (max(connects) + 1 if connects else 0)
    return (vertices, len(counts), len(connects), hash(counts), hash(connects))


def classify(old_key, new_key, old_points, new_points):
    """前と今のトポロジーの鍵・頂点の位置から、変更の種類 (CHANGE_*) を決める。"""
    if old_key != new_key:
        return CHANGE_TOPOLOGY
    if list(old_points) != list(new_points):
        return CHANGE_POINTS
    return CHANGE_NONE


class SessionBook(object):
    """トポロジーの鍵ごとのセッション (最近使ったものを limit 個まで)。

    factory(graph) -> PathSession。セッションの graph が今のものと違えば setGraph で入れ替える
    (位置が変わったときと、前のトポロジーに戻ったとき)。
    """

    def __init__(self, factory, limit=4):
        self._factory = factory
        self._limit = max(1, int(limit))
        self._entries = []   # [(鍵, セッション)]。最後が最近使ったもの
        self.current = None

    def __len__(self):
        return len(self._entries)

    def keys(self):
        return [key for key, _session in self._entries]

    def sessions(self):
        """覚えているセッションすべて (古い順)。"""
        return [session for _key, session in self._entries]

    def sessionFor(self, key, graph):
        """鍵のセッションと、状態 (STATUS_*)。"""
        for index, (known, session) in enumerate(self._entries):
            if known == key:
                del self._entries[index]
                status = STATUS_SAME if session is self.current else STATUS_RESTORED
                break
        else:
            session = self._factory(graph)
            status = STATUS_NEW
        if session.graph is not graph:
            session.setGraph(graph)
        self._entries.append((key, session))
        del self._entries[:-self._limit]   # 古いものから捨てる
        self.current = session
        return session, status
