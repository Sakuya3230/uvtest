"""
メッシュのどのエッジが UV の切れ目か (numpy だけ。Maya には触らない)。
"""

from __future__ import annotations

from ...compat.accel import np


def uv_seam_mask(edges, counts, connects, uv_counts, uv_ids):
    """エッジ (M, 2) ごとに、UV の切れ目なら True の bool の配列。

    counts / connects は面ごとの頂点の数と並び (MFnMesh.getVertices)、uv_counts / uv_ids は面の角ごとの UV の番号
    (MFnMesh.getAssignedUVs。UV の無い面は数が 0)。エッジの両側の面で、両端の頂点の UV の番号が違えば切れ目。
    面が片側にしか無いエッジ (メッシュの縁) も切れ目。
    """
    counts   = np.asarray(counts, dtype=np.int64)
    connects = np.asarray(connects, dtype=np.int64)
    edges    = np.asarray(edges, dtype=np.int64)
    if len(edges) == 0:
        return np.zeros(0, dtype=bool)

    # 角ごとの UV の番号 (UV の無い面の角は -1)
    corner_uv              = np.full(len(connects), -1, dtype=np.int64)
    has_uv                 = np.repeat(np.asarray(uv_counts, dtype=np.int64) > 0, counts)
    corner_uv[has_uv]      = np.asarray(uv_ids, dtype=np.int64)

    # 角ごとに、同じ面の次の角 (面の最後の角の次は、その面の最初の角)
    starts                 = np.cumsum(counts) - counts
    following              = np.arange(len(connects)) + 1
    following[starts + counts - 1] = starts

    # 角から次の角へのエッジを、小さい頂点 -> 大きい頂点の向きにそろえる (UV もそれに合わせる)
    v0, v1 = connects, connects[following]
    u0, u1 = corner_uv, corner_uv[following]
    swap   = v0 > v1
    low    = np.where(swap, v1, v0)
    high   = np.where(swap, v0, v1)
    u_low  = np.where(swap, u1, u0)
    u_high = np.where(swap, u0, u1)

    base   = int(max(edges.max(), connects.max())) + 1
    keys   = low * base + high
    order  = np.argsort(keys, kind="stable")
    keys, u_low, u_high = keys[order], u_low[order], u_high[order]

    # 同じエッジが続く所で UV が違えば切れ目。1 回しか出てこないエッジ (縁) も切れ目
    same      = keys[1:] == keys[:-1]
    differ    = same & ((u_low[1:] != u_low[:-1]) | (u_high[1:] != u_high[:-1]))
    unique, occurrences = np.unique(keys, return_counts=True)
    seam_keys = np.concatenate([keys[1:][differ], unique[occurrences == 1]])

    edge_keys = np.minimum(edges[:, 0], edges[:, 1]) * base + np.maximum(edges[:, 0], edges[:, 1])

    return np.isin(edge_keys, seam_keys)
