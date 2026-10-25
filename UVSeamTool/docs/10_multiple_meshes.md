# 段階 10: 複数のメッシュ

## 目的

ツールにしたときに選んでいたメッシュすべてを対象にする (前は最初の 1 つだけ)。

| 点 | 決め方 |
|---|---|
| 対象 | ツールにしたときに選んでいたメッシュすべて + ツールを使っている間に選んだメッシュ (下の「追加」) |
| 拾う | マウスの下で、いちばん手前のメッシュの頂点 |
| 作成中のガイド | 全体で 1 本。作成中に別のメッシュをクリックしたら、今のガイドを確定してから、そのメッシュで新しいガイドを始める |
| プレビュー | 作成中のガイドと同じメッシュの上だけ |
| 編集 | どのメッシュのガイドも選べる。ガイドは (メッシュの鍵, ガイドの id) の組 (ref) で指す |
| メッシュにまたがる削除・カット / 縫合 | 1 回の Undo |
| メッシュが消された | そのメッシュだけを対象から外す。全部消えたらツールを抜ける |

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [tool/targets.py](../tool/targets.py) | `Targets`: TargetMesh の集まり。`find(鍵)`・`remove(鍵)`・`pick(x, y)` -> (TargetMesh, 頂点) |
| [utils/picking.py](../utils/picking.py) | `pick_vertex(meshes, x, y)`: レイが当たったメッシュのうち、いちばん手前 (`closestIntersection` のレイの上の長さが小さい) のもの |
| [utils/undo.py](../utils/undo.py) | `chunk(名前)`: 中の Maya のコマンド (polyMapCut など) を 1 回の Undo にまとめる |
| [tool/guide_edit.py](../tool/guide_edit.py) | `apply_many([(TargetMesh, 組)])`: 複数のメッシュの組を 1 回の Undo で変える (`apply` はその 1 つだけの形) |
| [tool/uv_apply.py](../tool/uv_apply.py) | `apply_targets([(TargetMesh, ガイド)], 操作)`: メッシュごとに当てて、全部で 1 回の Undo |
| [tool/create_tool.py](../tool/create_tool.py) | `Targets` を受け取る。作成中のガイドがあるメッシュを `_active()` で探す。PathPreview はメッシュごと |
| [tool/edit_tool.py](../tool/edit_tool.py) | `Targets` を受け取る。選択・ホバー・ドラッグを ref (メッシュの鍵付き) で持つ |
| [tool/context.py](../tool/context.py) | `Targets` と、メッシュごとの `MeshWatcher` (どのメッシュの知らせかを鍵で覚える) |

## 仕組み

- **作成中のガイドは「どのメッシュの組に active_id があるか」で探す**: 状態をサブツールに別に持たない。ガイドの組
  (guide_store) が正なので、Undo で作成中に戻っても、そのメッシュが作成中のメッシュになる
- **ガイドの指し方を ref に**: ガイドの id はメッシュごとに 0 から付くので、メッシュをまたぐと重なる。選択・点・ホバーは
  (メッシュの鍵, ガイドの id) の組で持つ。core の拾う関数 (`nearest_guide` など) は id の中身を見ないので、そのまま使える
- **1 回の Undo にまとめる**: ガイドの組の変更は、自分の Undo のコマンド 1 回の中で全部のメッシュを書く (`apply_many`)。
  polyMapCut / polyMapSew は Maya のコマンドなので、`undoInfo` のチャンク (`undo.chunk`) で包む

## 落とし穴

- 選択を外すとき・メッシュを外したときは、`refresh` で無くなった ref を選択から外す (消したメッシュの ref を引くと失敗する)
- メッシュの鍵 (MObjectHandle の hashCode) で同じメッシュかを比べる。TargetMesh 同士は `is` で比べる
- マウスを動かすたびに、全部のメッシュにレイを当てている。メッシュが多い・大きいと重くなる (索引 accelParams は後で)

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); cmds.polyCube(); cmds.move(3, 0, 0); cmds.select("pSphere1", "pCube1")
UVSeamTool.tool()
# 球に点を 2 つ -> 立方体をクリック -> 球のガイドが確定し、立方体で新しいガイドが始まる
# [編集] -> 球と立方体のガイドを Shift+クリックで選ぶ -> [カット] -> Ctrl+Z 1 回で両方戻る / Delete -> Ctrl+Z
# 立方体を消す -> 「消されたメッシュを対象から外しました」・球はそのまま使える
```

mayapy (2022 / 2027) で、作成中に別のメッシュを押したときの確定と新しいガイド・メッシュにまたがるカットと削除が
1 回の Undo で戻ることを確かめた (マウスで拾う所は差し替えた。ビューでの拾い方は GUI で)。

## 追加: ツールを使っている間に選んだメッシュを足す

ツールを使っている間にメッシュを選ぶと (トランスフォーム・シェイプ・コンポーネントのどれでも)、対象に加わる。
選択を外しても、対象からは外さない (旧版と同じ)。ツールを始めるときにメッシュを選んでいる決まりは、そのまま。

```
選択が変わる -> SelectionWatcher (utils)         SelectionChanged を受け、手すきのときに 1 回だけ (矩形選択などで続けて届くため)
  -> Context._on_selection_changed
       selected_meshes() のうち、まだ対象でないものを Targets.add で加え、MeshWatcher を付ける
```

| ファイル | 中身 |
|---|---|
| [utils/selection_watcher.py](../utils/selection_watcher.py) | `SelectionWatcher(on_change)`・`release()` |
| [tool/targets.py](../tool/targets.py) | `add(mesh)` (もう対象なら None) |
| [tool/context.py](../tool/context.py) | ウォッチャーを付ける / 外す・`_on_selection_changed` |

- 作成・編集のモードは Maya の選択を使わない (段階 15)。メッシュを加えるのは、アウトライナーで選ぶか、選択のモードで選んだとき
- mayapy で、`add` (2 回目は None)・続けて選択しても予約は 1 回・外したあとは届かないことを確かめた

```python
cmds.polySphere(); UVSeamTool.tool()
cmds.polyCube()   # 作ったメッシュが選ばれる -> 「対象に加えました: pCube1」 -> 立方体にもガイドを作れる
```
