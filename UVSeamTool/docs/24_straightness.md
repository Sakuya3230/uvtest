# 段階 24: まっすぐさ (曲がりの少ないパス)

## 目的

長さだけの最短パスは、格子のメッシュでは階段状にジグザグしやすい (同じ長さの道がたくさんあり、どれを選ぶかは偶然)。
シームはまっすぐなほうが扱いやすいので、曲がりにコストを付けて、曲がりの少ないパスを選べるようにする (仕様の U13)。
旧 UVPathCut の段階 15 と同じ考え方 (numpy と scipy の版だけ)。

```
重み 0 (長さだけ)          重み 1 (曲がりを避ける)
S ─┐                        S ──────────┐
   └─┐                                  │
     └─┐                                │
       └─ G                             G
```

## コスト

```
1 歩のコスト = エッジの長さ + 重み × 平均のエッジの長さ × (1 - cos 曲がり角)
```

- まっすぐなら 0、直角なら「重み × 平均の長さ」(重み 1 = 直角 1 回はエッジ 1 本ぶんの遠回りと同じ)、折り返すほど大きい
- 平均の長さを掛けるので、メッシュの大きさ (単位) によらず同じ重みが同じように効く
- 設定「まっすぐさ」(分類「パス」、0〜10、既定 1.0)。0 なら今までの長さだけの最短パス

## 仕組み

曲がり角は「どのエッジから来たか」で決まるので、頂点ではなく **向き付きのエッジ** (状態。エッジ e を a -> b なら 2e、
b -> a なら 2e + 1) を節にして探す。

```
MeshGraph(位置, エッジ, turn_weight)          重みはグラフが持つ (区間を求める所すべてに重みを渡して回らない)
path_trees.path_tree(graph, 始点)             重み > 0 なら TurnPathTree、0 なら今までの PathTree (同じ使い方)
  使う所: PathPreview (作成のプレビュー)・shortest_path (区間を求める solve・点の削除でつなぎ直す)・PointDrag (点のドラッグ)
TurnPathTree
  _turn_steps (グラフごとに 1 回。MeshGraph.cached)
    状態の出る頂点 / 着く頂点、状態 p -> 「p の着く頂点から出る状態」(U ターンを除く) のつながりと曲がりの量 1 - cos を
    numpy でまとめて作る (出る頂点の順に並べた表から範囲を取り出す。ループなし)
  始点ごと: 仮の始点 -> 始点から出る状態 (コスト = そのエッジの長さ) を足した疎行列で dijkstra を 1 回
  pathTo(goal): goal に着く状態のうち最も安いものから、前の状態をたどる
設定を変えたら ToolActions._apply_straightness: 対象のグラフに setTurnWeight -> サブツールの targetChanged (プレビューの木を作り直す)
```

- 今あるガイドの区間は変えない (区間は求めた頂点の列を持っている)。次に求める区間から効く
- グラフは向きが無いので、点のドラッグの「後の点 -> 新しい位置 の道を逆にする」はそのまま使える (曲がりのコストは逆向きでも同じ)

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [core/path/turn_path_tree.py](../core/path/turn_path_tree.py) | `TurnPathTree`・`_turn_steps` |
| [core/path/path_trees.py](../core/path/path_trees.py) | `path_tree(graph, start)` (重みでどちらの木かを選ぶ) |
| [core/path/mesh_graph.py](../core/path/mesh_graph.py) | `turn_weight`・`turnWeight` / `setTurnWeight`・`positions` / `edges`・`cached` |
| [core/path/shortest_path.py](../core/path/shortest_path.py) / [path_preview.py](../core/path/path_preview.py) / [core/guide/point_drag.py](../core/guide/point_drag.py) | `path_tree` から木を作る |
| [core/settings/definitions.py](../core/settings/definitions.py) | `straightness` (分類「パス」) |
| [tool/target_mesh.py](../tool/target_mesh.py) / [api.py](../api.py) | グラフを作るときに設定の重みを渡す |
| [tool/tool_actions.py](../tool/tool_actions.py) | 設定を変えたら今のグラフへ (`_apply_straightness`) |

## 速さ (球 2.4 万頂点、mayapy)

| | 2027 | 2022 |
|---|---|---|
| 最初の始点 (つながりを作る + 探す) | 65 ms | 89 ms |
| 2 回目からの始点 | 19 ms | 58 ms |
| たどる 1 回 | 0.1 ms | 0.1 ms 未満 |
| (参考) 重み 0 の PathTree | 1 ms | 3 ms |

始点が変わるのは点を足したとき・ドラッグを始めたときだけ (マウスを動かすたびは木をたどるだけ)。

## 落とし穴

- 疎行列では値 0 が「辺が無い」になる。コスト 0 の辺はごく小さい値 (`_TINY`) にする
- 位置が変わるとグラフを作り直す (つながりも作り直しになる)。重みはそのとき設定から入る

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polyPlane(sx=20, sy=20); UVSeamTool.tool()
# 角の頂点をクリック -> 反対の角にマウスを乗せる -> L 字のプレビュー (曲がり 1 回)
# ツール設定のウィンドウの「パス」で「まっすぐさ」を 0 -> 階段状になることがある (長さは同じ)
```

mayapy (2027・2022) で、20x20 の平面の角から角が 重み 0 で曲がり 3〜4 回 -> 重み 1・5 で 1 回 (長さは同じ 2.0)、
向きを逆にしても曲がりと長さが同じことを確かめた。
