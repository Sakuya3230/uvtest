# 段階 2b: プレビューの描画

## 目的

マウスを動かすと、最後の点からマウスの下の頂点までの最短パスを描く。作った区間・置いた点・マウスの下の頂点も描く。

| 色 | 描くもの |
|---|---|
| マゼンタ (太) | 作った区間 |
| 黄 | 最後の点からマウスの下までのプレビュー |
| 緑 (大きい点) | 置いた点 |
| 橙 (点) | マウスの下の頂点 |

## 流れ

```
マウスを動かす (ボタンを押さずに)
  -> UVSeamToolContext.doPtrMoved
     -> CreateTool.hover                     マウスの下の頂点が変わったときだけ True
        -> picking.vertex_under_cursor (utils)
        -> GuideCreation.previewTo (core)    最後の点からの PathTree を使い回す
     -> view.refresh() (utils)               変わったら描き直しを頼む
描き直し (ビューを描き直すたび。カメラを回しても)
  -> UVSeamToolContext.drawFeedback
     -> CreateTool.draw(Painter)             区間・プレビュー・点を描く
        -> Painter.polyline / dots           MUIDrawManager で描く
```

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [core/path/path_tree.py](../core/path/path_tree.py) | `PathTree`: 始点から全頂点へ dijkstra を 1 回だけ解いて、`pathTo(goal)` で何度でも引く |
| [core/path/shortest_path.py](../core/path/shortest_path.py) | `PathTree` を 1 回だけ使う形に (中身の重複を無くした) |
| [core/guide/guide_creation.py](../core/guide/guide_creation.py) | `previewTo(vertex)`: 最後の点からの PathTree を覚え、最後の点が変わるまで使い回す |
| [utils/view.py](../utils/view.py) | `view_ray`・`refresh`・`camera_position` (picking からレイを移した) |
| [utils/mesh.py](../utils/mesh.py) | `worldPoints()` (描画用のワールドの位置) |
| [tool/painter.py](../tool/painter.py) | `Painter`: drawFeedback 1 回分の描き手 (`polyline` / `dots`)。サブツールは MUIDrawManager を直接使わない |
| [tool/sub_tool.py](../tool/sub_tool.py) | `hover(x, y)`・`draw(painter)` を足した |
| [tool/create_tool.py](../tool/create_tool.py) | ホバー・プレビュー・描画 |
| [tool/context.py](../tool/context.py) | `doPtrMoved`・`drawFeedback`。押した・キーのあとに描き直しを頼む |

## 仕組み

- **マニピュレータを使わない**: 旧 UVPathCut はマウスの移動を受け取るためにマニピュレータ (`registerForMouseMove` / `doMove`) を
  使っていたが、API 2.0 の MPxContext にも `doPtrMoved` (ボタンを押さずに動かした) がある (contextTour で確認済み)。
  描画も、ビューを描き直すたびに呼ばれる `drawFeedback` で描ける。コンテキストだけで済むので、ノードの登録も要らない
- **dijkstra は最後の点が変わったときだけ**: `previewTo` は最後の点からの `PathTree` を覚えておく。マウスを動かすたびに
  求めるのは「前の頂点をたどる」だけ (パスの長さの分)。点を足す・消すと最後の点が変わり、次のプレビューで作り直す
- **描き直しは変わったときだけ頼む**: `hover` はマウスの下の頂点が変わったときだけ True を返し、コンテキストが
  `view.refresh()` を呼ぶ。描くのは Maya が `drawFeedback` を呼んだとき (カメラを回しても残る)
- **ちらつきを避ける**: 面に重ねて描くと奥行きの比べ合いで面に負けるので、描く点をカメラへ距離の 0.2% 寄せる
  (`Painter._toward_camera`。旧版と同じ方法)

## 落とし穴

- `drawFeedback` で文字 (`text2d`) を描くと 2 重に描かれる (contextTour で確認済み)。線・点は問題ない。
  文字が要るようになったら、マニピュレータの `drawUI` で描く
- `drawFeedback` のスタブには event も引数にあるので、後ろの 2 つ (drawMgr, frameContext) を使う
- 描画用の位置 (`worldPoints`) とグラフは、ツールを有効にしたときに 1 回読むだけ。メッシュを動かすとずれる
  (外部の変更の検知 U64 で直す)
- `closestIntersection` を毎回、索引 (accelParams) なしで呼んでいる。大きいメッシュでホバーが重ければ、索引を持たせる
- 点を足すとき (`add_point`) は、プレビューの PathTree とは別に dijkstra を解いている (クリックごとに 1 回なので今は気にしない)

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere()
UVSeamTool.tool()
# 球の上でマウスを動かす -> 橙の点。クリック -> 緑の点。動かす -> 黄のプレビュー。もう一度クリック -> マゼンタの区間
# カメラを回しても残る / Delete・Esc・Enter で描画が変わる
```

mayapy (2022 / 2027) で、`previewTo` が最後の点からの PathTree を使い回し、点を足すと作り直すこと、描画で使う
API (`MFrameContext.kViewInverseMtx`・`MUIDrawManager.lineStrip` など) があることを確かめた。描画そのものは GUI で確かめる。
