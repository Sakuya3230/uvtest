# 段階 5a: ガイドを選ぶ・消す (編集のモード)

## 目的

編集のモードで、ガイドを選べるようにする。カット / 縫合は選んだガイドに当てる。点の移動 (5b)・挿入と削除 (5c) の前の段階。

| 操作 | 動き |
|---|---|
| 左クリック (ガイドの線の近く) | そのガイドだけを選ぶ |
| Shift / Ctrl / Ctrl+Shift + クリック | 切り替え / 外す / 足す (Maya と同じ) |
| 何も無い所をクリック | 選択を外す。クリックは Maya の普通の選択に渡す |
| マウスを乗せる | マウスの下のガイドを明るく描く |
| Delete | 選んだガイドを消す (Ctrl+Z で戻る) |
| Esc | 選択を外す |
| カット / 縫合のボタン | 選んだガイド (選んでいなければ警告) |

## 決めたこと (ユーザーの選択)

- **選択は Undo に積まない**。編集のサブツールが持つだけ。Ctrl+Z はガイドの形の変更だけを戻す。
  Undo で消えたガイドは、選択から自動で外れる (`refresh`)

## 流れ

```
クリック -> EditTool.press
  -> _guide_at(x, y)
       各ガイドの線 (TargetMesh.guidePositions) -> view.world_to_view (utils) で画面の点に
       -> guide_picking.nearest_guide (core)    線分までの距離が 8 ピクセル以内でいちばん近いもの
  -> guide_picking.combine_selection (core)     修飾キーで選択を変える
Delete -> EditTool.delete -> set_editing.remove_guides (core) -> guide_edit.apply (Undo できる 1 回)
```

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [core/guide/guide_picking.py](../core/guide/guide_picking.py) | `nearest_guide(画面の線, 位置, 距離)`・`combine_selection(選択, id, shift, ctrl)`。Maya に依存しない |
| [core/guide/set_editing.py](../core/guide/set_editing.py) | `remove_guides(組, id の集合)` (作成中のガイドを消したら作成中でなくなる) |
| [utils/view.py](../utils/view.py) | `world_to_view(点の列)`: ワールド -> ビューのピクセル (左下が原点。MEvent と同じ) |
| [tool/target_mesh.py](../tool/target_mesh.py) | `guidePositions(guide)`: ガイドの線全体のワールドの位置 |
| [tool/guide_drawing.py](../tool/guide_drawing.py) | `draw_guides(..., selected, hovered)`: 選んでいるもの (橙・太) とマウスの下のもの (明るい水色。今は明るいマゼンタ) |
| [tool/edit_tool.py](../tool/edit_tool.py) | 選択・ホバー・Delete・Esc・カット / 縫合 |
| [tool/context.py](../tool/context.py) | 押したあと・キーのあとは、受け取らなくても描き直す (選択が変わっていることがあるため) |

## 仕組み

- **拾うのは画面の上で**: ガイドの線を画面のピクセルに写し、マウスから線分までの距離で比べる。計算そのもの
  (`nearest_guide`) は画面の座標だけを見るので core に置ける (写すのは utils)
- **選択はサブツールの中**: `frozenset` の id。ガイドの組 (GuideSet) には入れないので Undo に積まれない。
  ガイドの組が変わったら (`refresh`) 無くなった id を外す
- **何も無い所のクリックは Maya に渡す**: 選択を外したうえで `press` が False を返し、コンテキストが基底の選択に任せる

## 落とし穴

- メッシュの裏に回ったガイドも拾える (隠れているかは見ていない)。必要なら面の前後を比べる
- マウスを動かすたびに全ガイドの線を画面に写している。ガイドが多くて重ければ、カメラが変わったときだけ写し直す
- 作成のモードで作成中のガイドがあるまま編集のモードにして消すと、作成中でなくなる

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()
# 作成でガイドを 2〜3 本作る (Enter で確定) -> [編集]
# 線にマウスを乗せる (明るくなる) -> クリック (橙) -> Shift+クリックで足す -> [カット]
# Delete で消す -> Ctrl+Z で戻る
```
