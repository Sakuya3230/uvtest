# 段階 5: グラフと最短パス (numpy / scipy を使う)

[目次](README.md) ・ 前: [段階 4](04_picking.md)

## 目的

- メッシュの頂点とエッジを **グラフ** にして、端点 (頂点かエッジ) のあいだの **最短パス** を求める
- 「スタートを決めたときに 1 回だけ探し、ホバーのたびには道をたどるだけ」にする (`PathTree`)
- scipy があれば scipy で、無ければ Python で、同じ長さの最短パスを返す

この段階では、まだ画面には何も出ない (プレビューは段階 6)。

## 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/accel.py:38](../core/accel.py#L38) `scipy_modules` | numpy / scipy が使えるかを 1 回だけ調べる。[set_enabled:52](../core/accel.py#L52) で使わないようにもできる |
| [core/graph.py:26](../core/graph.py#L26) `MeshGraph` | 頂点・エッジ・長さ・隣接リスト (隣, エッジ, 長さ)・x/y/z の別のリスト |
| [core/graph.py:78](../core/graph.py#L78) `edgeBetween` | 2 頂点を結ぶエッジ (表は最初に使うときに作る) |
| [core/graph.py:84](../core/graph.py#L84) `matrix` | scipy の疎行列 (使えなければ None。最初に使うときに作る) |
| [core/path.py:33](../core/path.py#L33) `Waypoint` / [:56](../core/path.py#L56) `PathResult` | 端点 / 最短パス (頂点の列・エッジの列・長さ) |
| [core/path.py:89](../core/path.py#L89) `shortest_path` | Python の A* |
| [core/path.py:76](../core/path.py#L76) `_finish` | 端点がエッジなら、そのエッジを先頭 / 末尾に足す |
| [core/path.py:161](../core/path.py#L161) `PythonPathTree` | ゴールごとに A* して覚える |
| [core/path.py:177](../core/path.py#L177) `ScipyPathTree` | スタートから全頂点を `csgraph.dijkstra` で 1 回探し、前の頂点をたどる |
| [core/path.py:217](../core/path.py#L217) `path_tree` | scipy が使えれば ScipyPathTree、無ければ PythonPathTree |
| [scene/mesh.py:109](../scene/mesh.py#L109) `mesh_graph` / [:163](../scene/mesh.py#L163) `MeshModel.graph` | Maya のメッシュからグラフを作る (1 回だけ) |
| [tests/UVPathCut/test_path.py](../../tests/UVPathCut/test_path.py) | グラフと A* (pytest 8 件。scipy の 1 件は pytest では飛ばす) |
| [tests/UVPathCut/mayapy/test_path.py](../../tests/UVPathCut/mayapy/test_path.py) | scipy と Python が同じ長さになるか・時間 (mayapy 4 件) |
| [tests/UVPathCut/mayapy/run_all.py](../../tests/UVPathCut/mayapy/run_all.py) | その Maya の版の site-packages (numpy / scipy) を PYTHONPATH に足して実行する |

## 仕組み

### グラフ

```
MeshGraph(points, edges)
  points[v]      頂点 v の (x, y, z) (ワールド)
  edges[e]       エッジ e の (頂点 0, 頂点 1)   ← エッジの番号 = Maya のエッジの番号
  lengths[e]     エッジ e の長さ (重み)
  neighbors[v]   [(隣の頂点, エッジ, 長さ)]
```

UV のカット / 縫合では頂点・位置・エッジが変わらないので、グラフは作り直さない。
Maya からエッジの両端を読むのは 1 本ずつ (`getEdgeVertices`)。9 万エッジで 100 ms ほどかかるが、
ツールに入ったときの 1 回だけ。

### 端点がエッジのとき

- **スタートがエッジ**: 両端の頂点から同時に (距離 0 で) 探し始め、できた道の先頭にそのエッジを足す
- **エンドがエッジ**: どちらかの端に着いたら (近いほう) ゴール。道の末尾にそのエッジを足す

両端から同時に始めるので、道がスタートのエッジ自体を通ることはない。

### 2 つの探し方 (PathTree)

```
tree = path_tree(graph, start)     スタートを決めたとき (段階 7) に 1 回
path = tree.pathTo(goal)           ホバーのたび
```

| | ScipyPathTree (scipy あり) | PythonPathTree (scipy なし) |
|---|---|---|
| 作るとき | `csgraph.dijkstra` でスタートから **全頂点** の最短距離と「ひとつ前の頂点」を求める | 何もしない |
| `pathTo` | ゴールから前の頂点をたどる (0.3〜0.5 ms) | A* で探して、ゴールごとに覚える |
| 4.5 万頂点 | 作る 2〜7 ms (+ 疎行列 20〜35 ms は 1 回だけ) | 極から極 60〜70 ms |

**ダイクストラ法** は、スタートから近い順に頂点を確定していく方法。全頂点まで進めると、
各頂点の「ひとつ前の頂点」が最短経路の木になり、どのゴールへの道もそこからたどれる。
**A\*** は、「ここまでの距離 + ゴールまでの直線距離 (見積もり)」の小さい順に調べるので、
1 つのゴールだけなら早く着く。直線距離は実際の道より短いので、最短が保証される。

scipy の `dijkstra(行列, indices=始点のリスト, return_predecessors=True, min_only=True)` は、
始点のどれかからの最短距離と前の頂点 (始点と届かない頂点は -9999) を返す。
アルゴリズム自体が C で書かれているので、Python の A* 1 回よりも、全頂点を探すほうが速い。

### numpy / scipy の扱い (core/accel.py)

- `scripts/site-packages/<Maya の版>` に入っていて、起動用のバッチが PYTHONPATH に足す
- バッチを通さない Maya や、pytest の Python (Anaconda の numpy が壊れている) では使えない。
  使えなければ Python の実装に戻る (`accel.scipy_modules()` が None)
- テスト: pytest では Python の実装を確かめ、mayapy で scipy と Python の結果が一致することを確かめる。
  mayapy のテストの `run_all.py` は、バッチと同じく site-packages を PYTHONPATH に足す

## 落とし穴

- 同じ長さの道が複数あると、scipy と Python で選ぶ道が違うことがある。テストは長さで比べる
- 疎行列では値 0 が「辺が無い」になる。長さ 0 のエッジはごく小さい値にする
- 疎行列は同じ (行, 列) が 2 回あると値を足す。同じ 2 頂点を結ぶエッジが 2 本あると長さが足される
  (普通のメッシュでは起きない)
- Maya の `polySelect -shortestEdgePath` は長さの最短ではない (本数が少ない道に寄る。旧版で確認)。
  答え合わせにはヒューリスティックなしのダイクストラ法を使う
- pytest で `accel` が numpy を試しに読むと、Anaconda の numpy が警告 (mkl-service) を出す。
  そのあと読み込みに失敗して Python の実装になる。害はない

## 試し方

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polySphere(subdivisionsAxis=300, subdivisionsHeight=150)
from UVPathCut.scene.mesh import MeshModel, target_mesh
from UVPathCut.core.path import Waypoint, path_tree
from UVPathCut.core import accel
model = MeshModel(target_mesh())
graph = model.graph()
tree = path_tree(graph, Waypoint("vertex", 0))
print(tree.backend, accel.available())                     # "scipy" True (バッチで起動していれば)
print(tree.pathTo(Waypoint("vertex", len(graph.points) - 1)))   # PathResult(149 本, ...)
model.release()
```
