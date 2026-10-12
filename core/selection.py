# -*- coding: utf-8 -*-
"""
選択のモードでツールが行う選択 (Maya に依存しない。段階 16d)。

    op = selection_op(shift, ctrl)            # 修飾キー -> REPLACE / TOGGLE / REMOVE / ADD (Maya と同じ)
    loop_op(op)                               # ダブルクリックのループに使う操作
    clicks = ClickTracker(interval=0.5)
    clicks.click(key, time) -> True ならダブルクリック (同じものを interval 秒以内に 2 回)
    marquee_edges(edges, positions, rect)     # 矩形にかかるエッジ (一部でも入るもの)

仕組み:
- はじめは選択のモードのクリックを Maya の選択 (MPxSelectionContext の基底) に任せたが、Maya の選択は
  Maya の対称で選択を両側にし (ツールの対称と二重になる)、隠れた裏側のエッジも拾う (プレビューと違う所が
  選ばれる)。合わせるために Maya の設定を一時的に書き換える仕組みまで要ったので、ツールで選ぶ形に作り直した
  (プレビューで拾ったものをそのまま選ぶので、表示と結果が必ず一致する)
- 修飾キーは Maya と同じ: なし = 置き換え、Shift = 切り替え、Ctrl = 外す、Ctrl+Shift = 足す
- ダブルクリックは Qt のダブルクリックのイベント (tool/keys.py のフィルターが受け取る)。Maya は
  2 回目の押下をコンテキストの doPress に届けなかった (GUI で確認)。ClickTracker (同じエッジを間隔の内に
  2 回) は、押下が届く場合の予備。1 回目のクリックの選択は、ループを選ぶ前に取り消す (Undo を 1 回にする)
"""
__all__ = ["REPLACE", "TOGGLE", "REMOVE", "ADD", "selection_op", "loop_op",
           "ClickTracker", "marquee_edges", "normalize_rect", "segment_hits_rect"]

REPLACE = "replace"
TOGGLE = "toggle"
REMOVE = "remove"
ADD = "add"


def selection_op(shift, ctrl):
    """修飾キーから選択の操作 (Maya と同じ)。"""
    if shift and ctrl:
        return ADD
    if shift:
        return TOGGLE
    if ctrl:
        return REMOVE
    return REPLACE


def loop_op(op):
    """ダブルクリックでループを選ぶときの操作。切り替え (Shift) は足す (1 回目のクリックで切り替えた
    エッジをもう一度切り替えて外さないように。Maya の Shift+ダブルクリックもループを足す)。"""
    return ADD if op == TOGGLE else op


class ClickTracker(object):
    """ダブルクリックを見分ける (同じものを interval 秒以内に 2 回)。

    3 回目は新しい 1 回目として数える (トリプルクリックでループを 2 回選ばない)。
    """

    def __init__(self, interval=0.5):
        self.interval = interval
        self._last = None   # (key, time)

    def click(self, key, now):
        last = self._last
        if last is not None and last[0] == key and now - last[1] <= self.interval:
            self._last = None
            return True
        self._last = (key, now)
        return False

    def reset(self):
        self._last = None


def normalize_rect(start, end):
    """2 点から (左, 下, 右, 上)。"""
    return (min(start[0], end[0]), min(start[1], end[1]), max(start[0], end[0]), max(start[1], end[1]))


def segment_hits_rect(pa, pb, rect):
    """画面の線分 pa-pb が矩形 rect (左, 下, 右, 上) に一部でもかかるか (Liang-Barsky の切り取り)。"""
    left, bottom, right, top = rect
    x0, y0 = pa
    dx, dy = pb[0] - x0, pb[1] - y0
    low, high = 0.0, 1.0
    for p, q in ((-dx, x0 - left), (dx, right - x0), (-dy, y0 - bottom), (dy, top - y0)):
        if p == 0.0:
            if q < 0.0:
                return False   # 矩形の辺に平行で、外側
            continue
        t = q / p
        if p < 0.0:
            if t > high:
                return False
            low = max(low, t)
        else:
            if t < low:
                return False
            high = min(high, t)
    return low <= high


def marquee_edges(edges, positions, rect):
    """矩形 rect (左, 下, 右, 上) に一部でもかかるエッジ (Maya の矩形選択と同じ)。

    edges は [(エッジの番号, 頂点 a, 頂点 b)]、positions は頂点 -> 画面の (x, y) か None (カメラの後ろ)。
    両端が画面に写るエッジだけを数える。はじめは「中点が入るもの」にしたが、半分ほど入れないと選ばれず
    使いにくかった (GUI で確認)。
    """
    left, bottom, right, top = rect
    result = []
    for edge, a, b in edges:
        pa, pb = positions[a], positions[b]
        if pa is None or pb is None:
            continue
        # 両端とも矩形の同じ側の外なら、かからない (多くのエッジはここで飛ばせる)
        if (pa[0] < left and pb[0] < left) or (pa[0] > right and pb[0] > right) or \
                (pa[1] < bottom and pb[1] < bottom) or (pa[1] > top and pb[1] > top):
            continue
        if segment_hits_rect(pa, pb, rect):
            result.append(edge)
    return result
