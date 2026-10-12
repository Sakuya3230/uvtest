# 段階 15: 曲がりの重み

[目次](README.md) ・ 前: [段階 14](14_multiple_meshes.md) ・ 次: [段階 16](16_select_mode.md)

## 目的

長さだけの最短パスは、格子のメッシュでは階段状にジグザグしやすい (同じ長さの道がたくさんあり、
どれを選ぶかは偶然)。UV のシームは、まっすぐなほうが扱いやすい。そこで曲がりにコストを付け、
曲がりの少ないパスを選べるようにする (設定「まっすぐさ」。0 で今までと同じ)。

```
重み 0 (長さだけ)          重み 1 (曲がりを避ける)
S ─┐                        S ──────────┐
   └─┐                                  │
     └─┐                                │
       └─ G                             G
```

## 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/turning.py](../core/turning.py) | 新規。曲がりの重み付きの最短パス |
| [core/turning.py:42](../core/turning.py#L42) `turn_scale` | 曲がりのコストの単位 = 平均のエッジの長さ |
| [core/turning.py:74](../core/turning.py#L74) `_first_states` / [:84](../core/turning.py#L84) `_goal_states` | スタート・ゴールに当たる状態 (向き付きのエッジ) |
| [core/turning.py:117](../core/turning.py#L117) `turn_shortest_path` / [:180](../core/turning.py#L180) `PythonTurnPathTree` | Python 版: 状態の A* (ゴールごと) |
| [core/turning.py:198](../core/turning.py#L198) `_transitions` | 状態のつながりと曲がりの量を numpy の配列で (グラフごとに 1 回。ループなし) |
| [core/turning.py:233](../core/turning.py#L233) `TurnPathTree` | scipy 版: 状態の疎行列に仮の始点 S を足し、dijkstra を 1 回 |
| [core/turning.py:99](../core/turning.py#L99) `path_cost` | パスのコストを数え直す (テスト・比べる用) |
| [core/path.py:219](../core/path.py#L219) `path_tree(turn_weight=)` | 重みが 0 より大きければ core.turning を使う |
| [core/path.py:64](../core/path.py#L64) `PathResult.cost` | 探したときのコスト (長さ + 曲がり) |
| [core/graph.py:45](../core/graph.py#L45) `MeshGraph.cache` | グラフから作ったものを置く場所 (位置が変われば新しいグラフと一緒に捨てる) |
| [core/session.py:95](../core/session.py#L95) `turn_weight` / [:109](../core/session.py#L109) `setTurnWeight` | セッションが重みを持つ。変えたらスタートから探し直す |
| [core/settings.py:66](../core/settings.py#L66) `straightness` | 設定「まっすぐさ」 (0〜10、既定 1.0、`-st`)。ツール設定のウィンドウの「パス」にスライダーが出る (表から) |
| [tool/context.py:189](../tool/context.py#L189) / [:447](../tool/context.py#L447) | セッションを作るときに渡す / 変えたら全メッシュ・全トポロジーのセッションへ |
| [tests/UVPathCut/test_turning.py](../../tests/UVPathCut/test_turning.py) | 曲がりが減る・長さと引き換え・素朴な Dijkstra と同じコスト・端点のエッジ・セッション (pytest 7 件) |
| [tests/UVPathCut/mayapy/test_path.py](../../tests/UVPathCut/mayapy/test_path.py) | scipy 版と Python 版のコストが一致・時間 |

## 仕組み

### コスト

```
1 歩のコスト = エッジの長さ + 重み × 平均のエッジの長さ × (1 - cos 曲がり角)
```

- まっすぐ (0°) なら 0、直角なら `重み × 平均の長さ`、鋭く折り返すほど大きい (最大 2 倍)
- 平均のエッジの長さを掛けるので、メッシュの大きさ (cm か m か) によらず同じ重みが同じように効く
- 重み 1 = 「直角に 1 回曲がるのは、エッジ 1 本ぶん遠回りするのと同じ」

### 状態を「向き付きのエッジ」にする

曲がり角は「どのエッジから来たか」で決まるので、頂点だけを状態にした今までの探索では数えられない。
状態を **向き付きのエッジ** (エッジ e を a → b に進んだら `2e`、b → a なら `2e + 1`) にし、
状態から状態へ (着いた頂点から出ていくエッジへ。U ターンは除く) 探す。

| | 状態 |
|---|---|
| スタートが頂点 | そこから出ていく状態 (コスト = そのエッジの長さ) |
| スタートがエッジ | そのエッジの両向き (コスト 0。その先の曲がりはこのエッジの向きから測る) |
| ゴールが頂点 | そこに着く状態のどれか (いちばん安いもの) |
| ゴールがエッジ | そのエッジを通った状態 (最後の曲がりも数える) |

### scipy 版

状態のつながりは「向き付きのエッジの数 × 平均の次数」ほど (4.5 万頂点の球で 18 万状態・54 万のつながり)。
Python のループで作ると遅いので、numpy でまとめて作る ([_transitions](../core/turning.py#L198)):

1. 出ていく状態を「出る頂点」の順に並べ (`argsort`)、頂点ごとの数 (`bincount`) と先頭の位置を作る
2. 状態 p の次の候補は「p の着く頂点から出る状態」の範囲。`repeat` と通し番号で全部を一度に並べる
3. U ターン (`to == from ^ 1`) を外し、曲がりの量 `1 - cos` を単位ベクトルの内積で求める

ここまではグラフごとに 1 回 (`graph.cache`)。重みはスタートのたびに掛ける。
スタートの最初のコストはエッジごとに違う (頂点のスタートはそのエッジの長さ) ので、
dijkstra の始点を複数にする (`min_only`。どれも 0 から始まる) 代わりに、**仮の始点 S** から最初の状態へ
最初のコストの辺を張って、S から 1 回だけ探す。

### 速さ (4.5 万頂点の球)

| | 2027 | 2022 |
|---|---|---|
| scipy 最初のスタート (つながりを作る + 探す) | 121 ms | 176 ms |
| scipy 2 回目からのスタート | 27 ms | 71 ms |
| scipy たどる 100 回 | 6 ms | 7 ms |
| Python 極から極 (scipy が無いとき) | 368 ms | 451 ms |
| Python 近い所 | 1 ms | 2 ms |

## 落とし穴

- 疎行列では値 0 が「辺が無い」になる。コスト 0 の辺 (エッジのスタートの最初の状態) はごく小さい値にする
- 見積もり (ゴールまでの直線距離) は、コストが長さ以上なので最短を壊さない。同じ頂点に着く状態は
  見積もりが同じなので、ゴールの頂点に着く状態を最初に取り出した時点で最短
- 位置が変わると新しいグラフになり (段階 13 の `withPoints`)、つながりも作り直しになる (`graph.cache` ごと捨てる)
- 重みが 0 のときは今までの頂点の探索を使う (状態の探索より速い)

## 試し方

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polyPlane(name="plane", subdivisionsX=20, subdivisionsY=20)
cmds.select("plane")
import UVPathCut; UVPathCut.tool()
# 1. 角の頂点をクリックしてスタート、反対の角にマウスを乗せる -> L 字のプレビュー (曲がり 1 回)
# 2. ツール設定のウィンドウで「まっすぐさ」を 0 にする -> 階段状 (長さは同じ)
#    スクリプトからは cmds.uvPathCutCtx("uvPathCutContext", e=True, straightness=0)
# 3. 球で、重みを 0〜5 に変えて極から極などを見比べる
```
