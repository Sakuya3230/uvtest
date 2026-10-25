"""
ガイドの組 <-> 保存する JSON の文字列 (docs/27_seamguide_spec.md の 6 章)。

    {"format": "UVSeamTool.guides", "version": 1,
     "topology": {"vertices": 382, "edges": 780, "hash": "..."},
     "active_id": null,
     "guides": [{"id": 0, "closed": false, "partner": null,
                 "points": [{"v": 0, "p": [x, y, z]}, ...],                    頂点の点
                 "segments": [{"mode": "shortest", "seam": [0, 1, ..., 105]}, ...]}]}

シーム (求めたエッジの道) は保存して正とする。"p" は控えの位置 (オブジェクト空間。トポロジーが変わったときに寄せ直す用。
書くときに位置を求める関数を渡したときだけ書く。読むときは今は使わない)。
version は 1 のまま (開発中なので、持ち方を変えたときに前の形の読み替えは作らない。前の形は読めない形として ValueError)。
"""

from __future__ import annotations

import json

from .guide import Guide
from .guide_point import vertex_point
from .guide_segment import GuideSegment
from .guide_set import GuideSet

FORMAT  = "UVSeamTool.guides"
VERSION = 1


def dumps(guide_set, topology, position_of=None):
    """ガイドの組とトポロジーの目印 (core.path.topology.topology_of) を JSON の文字列にする。

    position_of(点) を渡すと、点ごとに控えの位置 (x, y, z) を書く。
    """
    data = {
        "format":       FORMAT,
        "version":      VERSION,
        "topology":     topology,
        "active_id":    guide_set.active_id,
        "guides":       [_guide_to_dict(guide, position_of) for guide in guide_set.guides],
    }

    return json.dumps(data, separators=(",", ":"))


def loads(text):
    """JSON の文字列 -> (ガイドの組, トポロジーの目印)。形が違えば ValueError。"""
    data = json.loads(text)
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ValueError("UVSeamTool のガイドの形ではありません")

    if data.get("version") != VERSION:
        raise ValueError("知らない版です: {}".format(data.get("version")))

    try:
        guides    = tuple(_guide_from_dict(item) for item in data["guides"])
        guide_set = GuideSet(guides=guides, active_id=data.get("active_id"))
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise ValueError("ガイドを読めません ({})".format(error))

    return guide_set, data.get("topology")


def _guide_to_dict(guide, position_of):
    return {
        "id":       guide.id,
        "closed":   guide.closed,
        "partner":  guide.partner,
        "points":   [_point_to_dict(point, position_of) for point in guide.points],
        "segments": [_segment_to_dict(segment) for segment in guide.segments],
    }


def _segment_to_dict(segment):
    return {"mode": segment.mode, "seam": [int(v) for v in segment.seam]}


def _point_to_dict(point, position_of):
    data = {"v": int(point.vertex)}
    if position_of is not None:
        data["p"] = [round(float(c), 6) for c in position_of(point)]

    return data


def _guide_from_dict(item):
    points   = tuple(_point_from_dict(point) for point in item["points"])
    segments = tuple(GuideSegment(mode=segment["mode"], seam=tuple(int(v) for v in segment["seam"]))
                     for segment in item["segments"])
    partner  = item.get("partner")

    return Guide(id=int(item["id"]), points=points, segments=segments, closed=bool(item.get("closed", False)),
                 partner=None if partner is None else int(partner))


def _point_from_dict(data):
    return vertex_point(data["v"])
