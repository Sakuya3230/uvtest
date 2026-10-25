# 段階 5c: 点の挿入・選択・削除 (編集のモード)

## 目的

選んでいるガイドの線に点を挿入し、点を選んで消せるようにする。編集の基本 (選ぶ・動かす・挿入・消す) がそろう。

| 操作 | 動き |
|---|---|
| 選んでいるガイドの線にマウスを乗せる | 点を挿入できる頂点に白い点 |
| 選んでいるガイドの線をクリック | そこに点を挿入 (そのままドラッグで動かせる。挿入と移動で 1 回の Undo) |
| 点をクリック (動かさずに離す) | その点だけを選ぶ (赤) |
| Shift / Ctrl / Ctrl+Shift + 点をクリック | 点の選択の切り替え / 外す / 足す |
| Delete | 選んでいる点を消す (前後の点を最短パスでつなぎ直す)。点を選んでいなければ、選んでいるガイドを消す |
| Esc | 点の選択を外す (点を選んでいなければ、ガイドの選択を外す) |

選んでいないガイドの線のクリックは、今までどおりガイドの選択。

## 流れ

```
線をクリック -> EditTool.press
  -> _line_vertex_at -> guide_picking.nearest_line_vertex (core)    いちばん近い線分の、近い方の頂点
  -> editing.insert_point(guide, 区間の番号, 頂点) (core)            区間の頂点の列を 2 つに分けるだけ
  -> PointDrag(挿入したガイド, 番号) で、そのままドラッグ             離したときに 1 回だけ組に入れる
Delete -> EditTool.delete
  -> set_editing.delete_points(組, graph, 点の集合) (core)
       ガイドごとに、番号の大きい点から editing.delete_point
       途中の点: 前後の点を前の区間の作り方でつなぎ直す / 端の点: その区間を落とす / 点が 1 つになる: ガイドごと消す
  -> guide_edit.apply (Undo できる 1 回)
```

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [core/guide/editing.py](../core/guide/editing.py) | `insert_point(guide, 区間の番号, 頂点)`・`delete_point(guide, graph, 番号)` |
| [core/guide/set_editing.py](../core/guide/set_editing.py) | `delete_points(組, graph, 点の集合)` |
| [core/guide/guide_picking.py](../core/guide/guide_picking.py) | `nearest_line_vertex(画面の区間, 位置, 距離)`。`combine_selection` は点の選択にも使う |
| [tool/guide_drawing.py](../tool/guide_drawing.py) | 選んでいる点 (赤)・挿入できる場所 (白) の色 |
| [tool/edit_tool.py](../tool/edit_tool.py) | 挿入・点の選択・点の削除・Esc の順番 |

## 仕組み

- **挿入は求め直さない**: 区間はもともとエッジの上を通る頂点の列なので、挿入する頂点で 2 つに分ければ線の形は
  そのまま (挿入の前と後で、通るエッジは同じ)
- **挿入と移動を 1 回の Undo に**: 押したときは挿入したガイドを `PointDrag` に渡してプレビューにするだけ。
  離したときに 1 回だけ組に入れる (動かさずに離しても、挿入は確定する)
- **消すのは大きい番号から**: 同じガイドの点を複数消すとき、先に小さい番号を消すと残りの番号がずれる
- **点の選択は組が変わったら外す**: 点は (ガイドの id, 番号) で持つので、挿入・削除・Undo で番号がずれる
- **クリックとドラッグの見分け**: 点を押したあと、まだ同じ頂点の上なら動かしていないことにする (手の揺れ)。
  離したらクリック = 点を選ぶ

## 落とし穴

- 挿入できるのは区間の途中の頂点だけ (端の頂点は既にある点。点の拾い方が線より優先されるので、普通は点になる)
- 途中の点を消すと、前後の点の間を最短パスで引き直す。消す前の 2 区間をつないだ形とは違うことがある
- 区間の作り方が最短だけの今は `delete_point` が前の区間の作り方 (最短) でつなぎ直す。作り方を足したら、どちらの
  作り方を使うかを決める

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()
# 3 点のガイドを作って Enter -> [編集] -> 線をクリックで選ぶ
# 線の上 (白い点) をクリック -> 点が増える / クリックしたままドラッグ -> 増えた点が動く
# 点をクリック (赤) -> Shift+クリックで足す -> Delete -> Ctrl+Z
```

mayapy で、挿入 (線の形が変わらない・端の頂点では None)、途中と端の点の削除、複数のガイドの点をまとめて消す・
点が 1 つになったらガイドごと消す、線の上の頂点の拾い方を確かめた。
