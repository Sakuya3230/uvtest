# 段階 1: UI なしで ガイド -> 最短パス -> カット

## 目的

ツールの核 (ガイドを作る・区間を最短パスで求める・シームにする・UV をカットする) だけを、コンテキストも UI も
無しで動かす。あとで足すコンテキストは、この流れを呼ぶだけの薄い皮にする。

最小限の実装にしてある (Undo のコマンド・設定・保存・点の編集はまだ無い)。

## 流れ

[api.py](../api.py) の `cut_path(vertices, mesh_name=None)` が、上から順に呼ぶだけ。

```
cut_path([0, 105, 210], "pSphere1")
  0. utils/mesh.Mesh.fromName           トランスフォームの名前 -> Mesh (省くと utils/selection.selected_meshes の最初)
  1. Mesh.points / Mesh.edgeVertices    Maya から 位置 (N, 3) とエッジ (M, 2) の配列を読む
  2. core/path/MeshGraph(...)           配列からグラフ (疎行列) と「頂点の組 -> エッジ」の表を作る
  3. core/guide/editing.new_guide       点 1 つのガイド
     core/guide/editing.add_point x 2   点を足すたびに solvers.solve -> shortest_path で区間を求める
  4. core/seam/seam_edges               区間の頂点の列 -> エッジの番号
  5. utils/uv_editor.cut_edges          polyMapCut
```

Maya に触るのは 0・1・5 (utils) だけ。2〜4 (core) は配列とガイドしか見ない。

## 追加したもの

| ファイル | 中身 |
|---|---|
| [constants.py](../constants.py) | `TOOL_NAME`・`SETTINGS_PATH` (まだ使わない) |
| [compat/accel.py](../compat/accel.py) | numpy / scipy を読み込み `np` / `sparse` / `csgraph` を渡す。`require()` が無いときに止める |
| [utils/log.py](../utils/log.py) | `debug` / `info` / `warning` / `error` (レベルは段階 2a のあとで足した。[coding_rules.md の 9](coding_rules.md#9-ログのレベル)) |
| [utils/node.py](../utils/node.py) | 名前 -> MObject (`mobject_from_name`) / MDagPath、フルパス・名前だけ、トランスフォーム <-> メッシュのシェイプ (中間オブジェクトは飛ばす) |
| [utils/mesh.py](../utils/mesh.py) | `Mesh`: メッシュのトランスフォーム 1 つ (MObjectHandle と MDagPath で持つ)。`fromName`・`points()`・`edgeVertices()` (numpy)・`edgeNames()` (cmds に渡す名前) |
| [utils/selection.py](../utils/selection.py) | `selected_meshes()`: 選択 (トランスフォーム・シェイプ・コンポーネント) -> Mesh のリスト |
| [utils/uv_editor.py](../utils/uv_editor.py) | `cut_edges` / `sew_edges` (Mesh とエッジの番号だけを受け取る) |
| [core/path/mesh_graph.py](../core/path/mesh_graph.py) | `MeshGraph`: 重みがエッジの長さの疎行列 (両向き)・`edgeBetween(a, b)` |
| [core/path/shortest_path.py](../core/path/shortest_path.py) | `shortest_path(graph, start, goal)`: scipy の dijkstra の「前の頂点」をたどる |
| [core/guide/guide_point.py](../core/guide/guide_point.py) / [guide_segment.py](../core/guide/guide_segment.py) / [guide.py](../core/guide/guide.py) | 値だけの入れ物 (frozen の dataclass) |
| [core/guide/solvers.py](../core/guide/solvers.py) | 作り方 -> 求める関数の表 `SOLVERS` (今は shortest だけ) |
| [core/guide/editing.py](../core/guide/editing.py) | `new_guide` / `add_point` (新しいガイドを返す) |
| [core/seam/seam.py](../core/seam/seam.py) | `seam_edges(guide, graph)` |
| [api.py](../api.py) | `cut_path` |
| [reloader.py](../reloader.py) | `MODULES` (依存の順) と `reload_modules()` |

## 仕組み

- **ガイドは変えられない値**: `add_point` は `dataclasses.replace` で点と区間を 1 つずつ足した**新しいガイド**を返す。
  前のガイドはそのまま残るので、後で Undo を「前と後のガイドの組を持つ」形で作れる
- **作り方の表**: `add_point` は最短パスを直接呼ばず `solvers.solve(mode, ...)` を通す。曲線などは表に足すだけ
- **最短パス**: `csgraph.dijkstra(..., indices=start, return_predecessors=True)` は全頂点への「前の頂点」を返す。
  goal から start まで戻って逆にする。届かない頂点は -9999
- **シーム**: 区間の頂点の列の隣どうしを `edgeBetween` でエッジの番号にする。区間の境目の頂点は前後で重なるので、
  同じエッジは 1 回だけ

## MeshGraph の中身

MeshGraph は **最短パスを解くための、メッシュのつながりの表**。Maya には触らず、numpy の配列 2 つ (位置 (N, 3)・
エッジ (M, 2)) から作る。2 x 1 の面の平面 (`cmds.polyPlane(sx=2, sy=1, w=2, h=1)`。頂点 6・エッジ 7) で見る。

```
頂点の番号            エッジの番号 (edges の行)
  3 --- 4 --- 5         (3,4)=5   (4,5)=6
  |     |     |         (0,3)=1   (1,4)=3   (2,5)=4
  0 --- 1 --- 2         (0,1)=0   (1,2)=2
```

`__init__` が作るものは 3 つ。

### 1. 重み = エッジの長さ

```python
lengths = np.linalg.norm(positions[edges[:, 0]] - positions[edges[:, 1]], axis=1)
```

各エッジの両端の位置を引いた長さ (この平面ではどれも 1.0)。これが「通る費用」なので、最短パスは
**見た目の距離が最短の道** になる。

### 2. 疎行列 `_matrix` (誰と誰が、どれだけの費用でつながっているか)

`[a, b]` が頂点 a から b へ行く費用。`.` はつながっていない。

```
     0  1  2  3  4  5
0 [  .  1  .  1  .  . ]      頂点 0 は 1 と 3 につながる
1 [  1  .  1  .  1  . ]      頂点 1 は 0・2・4 につながる
2 [  .  1  .  .  .  1 ]
3 [  1  .  .  .  1  . ]
4 [  .  1  .  1  .  1 ]
5 [  .  .  1  .  1  . ]
```

- **両向きに入れる** (`rows` と `columns` を入れ替えて 2 回分)。scipy の dijkstra は既定で向きのあるグラフとして
  解くので、(0, 1) だけだと 1 から 0 へ行けない
- **疎行列 (CSR) にする**。普通の行列だと頂点 10 万で 100 億マス。実際のつながりは 1 頂点に 4 つ前後なので、
  CSR はつながりの分 (エッジの数 x 2) だけを持つ

CSR の中身は 3 つの配列。

```
indptr  [0  2  5  7  9 12 14]                       頂点 i の隣は indices[indptr[i] : indptr[i+1]]
indices [1 3 | 0 2 4 | 1 5 | 0 4 | 1 3 5 | 2 4]     隣の頂点の番号
data    [1 1 | 1 1 1 | 1 1 | 1 1 | 1 1 1 | 1 1]    その費用 (長さ)
```

頂点 1 の隣は `indices[2:5]` = 0, 2, 4。dijkstra はこれを「今の頂点の隣はどれか」を引く表として使う。

### 3. `_edge_of` (頂点の組 -> エッジの番号)

```
{(0, 1): 0, (0, 3): 1, (1, 2): 2, (1, 4): 3, (2, 5): 4, (3, 4): 5, (4, 5): 6}
```

最短パスが返すのは **頂点の列** (0 -> 3 -> 4 -> 5)、`polyMapCut` に渡すのは **エッジの番号**。その変換が
`edgeBetween(a, b)`。`_key` で組を (小さい番号, 大きい番号) にそろえて引くので、(4, 5) でも (5, 4) でもエッジ 6。

### 使われ方

```
shortest_path(graph, 0, 5)
  -> csgraph.dijkstra(graph.matrix(), indices=0, return_predecessors=True)
     頂点 0 から全頂点への最短の費用と「1 つ前の頂点」(predecessors) を求める
  -> 5 から predecessors をたどって 0 まで戻り、逆にする -> (0, 3, 4, 5)
seam_edges(guide, graph)
  -> 隣どうしの (0,3) (3,4) (4,5) を edgeBetween で 1, 5, 6 に
```

この平面の 0 -> 5 は長さ 3 の道が 3 通り (0-1-2-5 / 0-1-4-5 / 0-3-4-5)。**同じ長さの道のどれを選ぶかは dijkstra
次第** で、こちらでは決めていない。後で入れる「まっすぐさ」(曲がりの少ない道を選ぶ重み) はこれを決めるためのもの。

### 今の作りの限界 (後の段階で考える)

| 点 | 今 | 影響 |
|---|---|---|
| いつ作るか | ツールを有効にしたとき 1 回 (`CreateTool.__init__`) | 頂点を動かす・トポロジーを変えると古いまま (外部の変更の検知 U64 で直す) |
| 位置の空間 | オブジェクト空間 | トランスフォームのスケールが軸ごとに違うと、見た目の最短とずれる |
| 作る速さ | `Mesh.edgeVertices` がエッジを 1 本ずつ読む | 大きいメッシュでは、ここが一番遅い |
| dijkstra の回数 | `add_point` のたびに、前の点から全頂点を解く | クリックだけなら十分速い。プレビュー (段階 2b) でマウスを動かすたびに解くのは無駄なので、前の点からの predecessors を 1 回だけ求めて使い回す |
| `_edges` | 持っているが、まだ使っていない | まっすぐさ (エッジの向きが要る)・描画で使う予定 |

## 落とし穴

- API 2.0 にはエッジの両端をまとめて読む関数が無い (`getEdgeVertices` を 1 本ずつ)。大きいメッシュで遅ければ後で見直す
- 選択がコンポーネント (頂点など) のとき、`getDagPath` はシェイプを返す。`node.mesh_transform_path` でトランスフォームに上げる
- 位置はオブジェクト空間 (スケールが軸ごとに違うトランスフォームでは、見た目の最短とずれる。上の表)
- Undo はまだ自分のコマンドではなく、`polyMapCut` そのものの Undo (1 回の cut_path で 1 回)

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere()                               # 作ったメッシュが選ばれる
guide, seam = UVSeamTool.cut_path([0, 105, 210])  # 選んでいるメッシュ (名前を渡すなら mesh_name="pSphere1")
print(guide)          # Guide(id=0, points=(GuidePoint(vertex=0), ...), segments=(GuideSegment(...), ...))
cmds.select(["pSphere1.e[{}]".format(e) for e in seam])   # 切ったエッジを見る
```

2022 / 2027 の mayapy で、球の UV が 439 -> 464 になり、Undo で 439 に戻ることを確かめた。
