# 段階 4: 頂点 / エッジを拾う

[目次](README.md) ・ 前: [段階 3](03_mesh_model_and_hover.md)

## 目的

- マウスの下の面 (段階 3) の角 / 辺から、マウスに最も近い頂点 / エッジを拾う
- 拾う処理を **Maya に依存しない純粋な関数** にして、pytest で確かめる
  (旧版では `MeshTarget` に依存していて、mayapy でしか確かめられなかった)
- 設定 `pickMode` (頂点 / エッジ) をリスナーでマニピュレータへ届け、変えたらその場で拾い直す

## 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/picking.py:18](../core/picking.py#L18) `PICK_VERTEX` / `PICK_EDGE` | 拾うものの名前 (設定 `pickMode` の選択肢と同じ) |
| [core/picking.py:40](../core/picking.py#L40) `Pick` | 拾った頂点 / エッジ (種類・番号・位置・面)。`key()` / `label()` |
| [core/picking.py:61](../core/picking.py#L61) `segment_distance` | 画面の点と線分の距離 |
| [core/picking.py:74](../core/picking.py#L74) `pick_component` | 面の角 / 辺を投影し、画面でマウスに最も近いものを選ぶ |
| [tool/drawing.py:40](../tool/drawing.py#L40) `view_projector` | ワールドの点を画面のピクセルへ投影する関数 (`worldToView`) |
| [tool/manipulator.py:94](../tool/manipulator.py#L94) `_update_pick` | 面 → (エッジのモードなら) 面の辺 → `pick_component`。変わったら描き直す |
| [tool/manipulator.py:75](../tool/manipulator.py#L75) `setPickMode` | 拾うものを替え、最後のマウスの位置で拾い直す |
| [tool/manipulator.py:123](../tool/manipulator.py#L123) `drawUI` | 面はうすく、拾った頂点は点・エッジは太線 (橙)、番号 |
| [tool/context.py:105](../tool/context.py#L105) `_on_setting_changed` | `pickMode` が変わったらマニピュレータへ (段階 1 のリスナーを初めて使う) |
| [tool/context.py:102](../tool/context.py#L102) | マニピュレータを作るときに今の `pickMode` を渡す |
| [tests/UVPathCut/test_picking.py](../../tests/UVPathCut/test_picking.py) | 拾い方 (pytest 5 件) |
| [tests/UVPathCut/mayapy/test_mesh.py](../../tests/UVPathCut/mayapy/test_mesh.py) | 実際のメッシュで hit → face_edges → pick_component (mayapy 1 件) |

## 仕組み

### 拾う流れ

```
doMove
  -> MeshModel.hit(レイ)                    面 (FaceHit: 頂点の番号と角の位置)
  -> MeshModel.face_edges(面)              面の辺 [(エッジ, 頂点 0, 頂点 1)]  (エッジのモードだけ)
  -> pick_component(面, 辺, モード, マウス, view_projector(view))
       頂点のモード  角を投影し、マウスとの距離が最も近い角
       エッジのモード 辺の両端を投影し、マウスとの (点と線分の) 距離が最も近い辺
  -> 拾ったもの (か面) が前と違えば view.refresh
```

### 画面で比べる理由

斜めから見た面では、ワールドの距離と見た目の距離が食い違う。たとえば手前に傾いた辺は、
ワールドでは近くても画面では遠く見える。ユーザーが見て狙っているのは画面の上の位置なので、
**投影してから画面の距離で比べる**。テスト `test_pick_uses_screen_distance` は、横に縮む投影で
「ワールドでは上の辺が近いが、画面では右の辺が近い」位置を作り、右の辺が選ばれることを確かめている。

### 点と線分の距離

線分 ab の上で点 p に最も近い点は `a + t (b - a)`。`t` は p を ab へ投影した割合
(`(p - a)・(b - a) / |b - a|²`) を 0〜1 に収めたもの。線分の外なら端点が最も近い。

### 投影の関数を受け取る

`pick_component` は投影を `project(点) -> (x, y)` という関数で受け取る。Maya では
`view_projector(view)` (`M3dView.worldToView`)、テストでは `front_view` のような決まった関数を渡す。
こうすると、マウスやビューが無くても拾い方を確かめられる (依存を引数で渡す)。

### 設定の変更を届ける

```
cmds.uvPathCutCtx(ctx, edit=True, pickMode="vertex")
  -> Settings.set -> リスナー UVPathCutContext._on_setting_changed("pickMode", "vertex")
       -> UVPathManip.setPickMode("vertex") -> 最後のマウスの位置で拾い直して描き直す
```

設定を変えた側 (コマンド。後の段階ではボタン・キー・ツール設定のウィンドウ) は、
何を更新するかを知らなくてよい。

## 落とし穴

- 面の辺の番号と角の並びの対応には頼らない。辺は `MItMeshPolygon.getEdges`、両端は
  `getEdgeVertices` で読む (`MeshModel.face_edges`)。辺の両端の位置は、面の頂点なので
  `FaceHit` の角の位置から引ける (Maya をもう一度呼ばない)
- 頂点のモードでは辺を読まない (要らない Maya の呼び出しを減らす)
- `worldToView` は 3 つの値 (x, y, クリップされていないか) を返す

## 試し方

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polySphere()
import UVPathCut; UVPathCut.tool()
# マウスに最も近い辺が橙の太線になり、e[番号] が出る

cmds.uvPathCutCtx("uvPathCutContext", edit=True, pickMode="vertex")
# マウスを動かさなくても、その場で最も近い角の点に変わる (vtx[番号])
```
