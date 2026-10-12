# -*- coding: utf-8 -*-
"""
コンポーネントの名前 (Maya に依存しない)。

    index_ranges([7, 3, 4, 5])               # [(3, 5), (7, 7)]
    edge_component_names("s", [1, 2, 3, 8])  # ["s.e[1:3]", "s.e[8]"]

polyMapCut などの MEL のコマンドにエッジを渡すとき、1 本ずつ書くとコマンドの文字列が長くなる
(何百本のパスなら何千文字)。続いている番号は範囲 (e[3:7]) にまとめる。
"""

__all__ = ["index_ranges", "edge_component_names"]


def index_ranges(indices):
    """番号を、続いている範囲 [(最初, 最後)] にまとめる (並べ替えて、重複を除いてから)。"""
    ranges = []
    for index in sorted(set(indices)):
        if ranges and index == ranges[-1][1] + 1:
            ranges[-1][1] = index
        else:
            ranges.append([index, index])
    return [tuple(r) for r in ranges]


def edge_component_names(shape, edges):
    """エッジを、MEL に渡すコンポーネントの名前 ("shape.e[3:7]" など) のリストにする。"""
    return ["{}.e[{}]".format(shape, first if first == last else "{}:{}".format(first, last))
            for first, last in index_ranges(edges)]
