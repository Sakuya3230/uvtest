"""
メッシュのトポロジー (頂点・エッジのつながり) の目印。
"""

from __future__ import annotations

import hashlib

from ...compat.accel import np


def topology_of(vertex_count, edges):
    """頂点の数とエッジ (M, 2) の配列から、トポロジーの目印の dict を作る。

    ガイドは頂点の番号で持つので、保存したときと目印が違えば (つながりが変わっていれば) そのガイドは使えない。
    位置は含めない (頂点を動かしただけなら、同じ目印)。
    """
    digest = hashlib.sha1(np.ascontiguousarray(edges, dtype=np.int64).tobytes()).hexdigest()

    return {"vertices": int(vertex_count), "edges": int(len(edges)), "hash": digest[:16]}
