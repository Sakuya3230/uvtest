# 段階 5b: 点を動かす (編集のモード)

## 目的

選んでいるガイドの点をドラッグで動かす。動かしている間は前後の区間だけを求め直してプレビューし、離したら 1 回の Undo で確定する。

| 操作 | 動き |
|---|---|
| ガイドを選ぶ | そのガイドの点 (緑) が出る |
| 点にマウスを乗せる | 点を大きく黄色で描く (線より点を優先して拾う) |
| 点をドラッグ | マウスの下の頂点に吸い付いて動く。前後の区間を最短パスで引き直してプレビュー |
| 離す | ガイドの組に入れる (1 回の Ctrl+Z で戻る) |
| ドラッグ中に Esc | やめる (組は変えていない。下の「ドラッグ中の Esc」) |
| メッシュの外へドラッグ | 最後の位置のまま |

Shift / Ctrl を押しながらのクリックは、点の上でもガイドの選択になる (点は動かさない)。

## 流れ

```
押す -> EditTool.press
  -> _point_at (選んでいるガイドの点を画面に写し、guide_picking.nearest_point で 10 ピクセル以内)
  -> PointDrag(guide, graph, index)                 (core) 前と後の点からの PathTree を 1 回だけ作る
ドラッグ -> EditTool.drag
  -> picking.vertex_under_cursor (utils)
  -> PointDrag.moved(vertex)                        木をたどるだけで、点を動かしたガイドを作る
  -> _drag_preview に置いて描く (draw_guides の replaced)
離す -> EditTool.release
  -> set_editing.replace_guide (core) -> guide_edit.apply (Undo できる 1 回)
```

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [core/guide/point_drag.py](../core/guide/point_drag.py) | `PointDrag`: 前後の点からの PathTree を持ち、`moved(vertex)` で点を動かしたガイドを返す |
| [core/guide/guide_picking.py](../core/guide/guide_picking.py) | `nearest_point(画面の点, 位置, 距離)` |
| [core/guide/set_editing.py](../core/guide/set_editing.py) | `replace_guide(組, ガイド)` (変わらなければ None) |
| [tool/guide_drawing.py](../tool/guide_drawing.py) | 選んでいるガイドの点を描く・`replaced` (ドラッグ中のプレビュー) |
| [tool/edit_tool.py](../tool/edit_tool.py) | 点のホバー・ドラッグ・離して確定・Esc でやめる |
| [tool/context.py](../tool/context.py) | ドラッグで変わったとき・離したあとに描き直す |

## 仕組み

- **前後の点からの木を使い回す**: ドラッグの間、動くのは 1 つの点だけで、前と後の点は動かない。押したときに
  前の点・後の点からの PathTree を作れば、動かすたびに dijkstra を解かずに済む
- **後の区間は逆向きにする**: グラフは向きが無いので「後の点 -> 新しい位置」の最短パスを逆にすれば
  「新しい位置 -> 後の点」の区間になる
- **組に入れるのは離したときだけ**: 動かしている間はサブツールの `_drag_preview` に持つだけで、ガイドの組も Undo も
  変えない。離したときに 1 回だけ `guide_edit.apply` するので、1 回のドラッグが 1 回の Ctrl+Z になる
- **端の点**: 最初の点は後の区間だけ、最後の点は前の区間だけを求め直す

## 落とし穴

- 今は区間の作り方が最短だけなので、`PointDrag` は最短パスの木を使う。曲線などの作り方を足したら、その区間は
  solvers で求め直すようにする
- 点の上の Shift / Ctrl クリックは選択として扱う (修飾キーで点を動かす操作を後で足すときは、ここを分ける)
- 押した点が隣の点と同じ頂点になると、その区間は頂点 1 つだけになる (シームは 0 本。困ったら止める)

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()
# 3 点のガイドを作って Enter -> [編集] -> 線をクリックで選ぶ (緑の点が出る)
# 真ん中の点をドラッグ -> 前後の区間が付いてくる -> 離す -> Ctrl+Z で元の位置
```

mayapy で、真ん中・最初・最後の点を動かしたときの区間 (端の頂点と、最短パスと同じ長さ) と、点の拾い方を確かめた。

## 直したこと: ドラッグ中の Esc

最初は `EditTool.abort` (コンテキストの `abortAction`) でドラッグをやめるようにしたが、効かなかった (GUI で確認)。
**マウスのボタンを押している間は、Maya がコンテキストの `abortAction` を呼ばない** ため。

そこで、段階 3 の右クリックのフィルターを広げて [tool/view_input.py](../tool/view_input.py) の `ViewInputFilter` にし
(`tool/right_click.py` は消した)、ドラッグ中の Esc も Maya より先に受け取る。

```
Esc (ShortcutOverride / KeyPress) -> ViewInputFilter
  -> is_busy()  (Context._is_busy -> サブツールの isBusy: 点を動かしている間だけ True)
     True  -> ShortcutOverride は accept (Maya のホットキーより先に KeyPress を受け取る)
              KeyPress で cancel() (Context._on_cancel -> EditTool.cancel -> 描き直し)
     False -> 何もしない (いつもどおり abortAction)
```

- [tool/sub_tool.py](../tool/sub_tool.py) に `isBusy()` / `cancel()` を足した。途中の操作があるサブツールはこれを上書きする
- やめたあとに届く離し (`release`) は、ドラッグが無いので何もしない
- mayapy (offscreen。2022 / 2027) で、途中の操作がある間だけ Esc を受け取り、ほかのキー・途中でないときは渡すことを確かめた

## 直したこと: 選んだ点の描画と選択 (段階 15 のあと)

- 選んだ点 (赤) を、ガイドの組に入っている形から描いていたので、ドラッグの間その場に残っていた。動かしているガイドの点は
  プレビューのガイドから描く (`EditTool.draw`)
- 離して確定すると、ガイドの組が変わったときの `refresh` で点の選択が外れていた。動かしただけなら点の番号は変わらないので、
  選択を戻す (`EditTool.release`。挿入したときは番号がずれるので外したまま)
