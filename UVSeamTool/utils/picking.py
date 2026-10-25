"""
ビューの上の位置から、メッシュの頂点を拾う (表の面だけ)。
"""

import maya.api.OpenMaya as om

from .view import view_ray

_MAX_DISTANCE = 1.0e7   # レイを探す距離


def pick_face(meshes, x, y):
    """ピクセル (x, y) の下の表の面。(meshes の中の番号, 面の番号, 当たった点 (x, y, z))。当たらなければ (None, None, None)。

    全部のメッシュで、いちばん手前の表の面 (pick_vertex と同じ決め方)。
    """
    source, direction = view_ray(x, y)
    best              = (None, None, None)
    best_distance     = None
    for index, mesh in enumerate(meshes):
        hit = _front_hit(mesh, source, direction)
        if hit is not None and (best_distance is None or hit[0] < best_distance):
            best_distance = hit[0]
            best          = (index, hit[2], hit[3])

    return best


def pick_vertex(meshes, x, y):
    """アクティブなビューのピクセル (x, y) の下の頂点。(meshes の中の番号, 頂点の番号)。当たらなければ (None, None)。

    レイが当たる **表の面** (法線がレイと向き合う面) のうち、全部のメッシュでいちばん手前のもの。その面の頂点のうち、
    当たった点にいちばん近いもの。裏の面は飛ばすので、開いたメッシュを裏から見ると、奥の表の面を拾う。
    """
    source, direction = view_ray(x, y)
    best_index        = None
    best_vertex       = None
    best_distance     = None
    for index, mesh in enumerate(meshes):
        hit = _front_hit(mesh, source, direction)
        if hit is None:
            continue

        distance, vertex = hit[0], hit[1]
        if best_distance is None or distance < best_distance:
            best_index, best_vertex, best_distance = index, vertex, distance

    return best_index, best_vertex


def vertex_under_cursor(mesh, x, y):
    """メッシュ 1 つの、ピクセル (x, y) の下の頂点の番号 (表の面だけ)。当たらなければ None。"""
    return pick_vertex([mesh], x, y)[1]


def _front_hit(mesh, source, direction):
    # レイが当たる面を近い順に見て、最初の表の面の (レイの上の長さ, 当たった点にいちばん近い頂点, 面, 当たった点)。無ければ None
    # メッシュが持つ索引 (Mesh.rayMeshFn) を使うので、2 回目からは面の数によらず速い
    mesh_fn, accel_params = mesh.rayMeshFn()
    result                = mesh_fn.allIntersections(om.MFloatPoint(source), om.MFloatVector(direction), om.MSpace.kWorld,
                                                     _MAX_DISTANCE, False, accelParams=accel_params, sortHits=True)
    if result is None:
        return None

    points, distances, faces = result[0], result[1], result[2]
    for point, distance, face in zip(points, distances, faces):
        # 法線とレイが向き合っていれば (内積が負) 表の面
        if mesh_fn.getPolygonNormal(face, om.MSpace.kWorld) * direction >= 0.0:
            continue

        hit_point = om.MPoint(point)
        vertices  = mesh_fn.getPolygonVertices(face)
        vertex    = min(vertices, key=lambda v: mesh_fn.getPoint(v, om.MSpace.kWorld).distanceTo(hit_point))

        return distance, vertex, face, (hit_point.x, hit_point.y, hit_point.z)

    return None
