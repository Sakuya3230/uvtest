# 段階 12: 扱えないメッシュ

## 目的

カット / 縫合できない・思ったとおりにならないメッシュを、対象にしたときに知らせ、カット / 縫合では飛ばす (旧版と同じ判定)。

| メッシュ | 対象にしたとき | カット / 縫合 | ガイドの保存 |
|---|---|---|---|
| シェイプがロックされている (lockNode) | 警告 (ガイドは作れるが、カット / 縫合と保存はできない) | そのメッシュは飛ばして警告 | しない (debug のログだけ) |
| インスタンス | 知らせる (ほかのインスタンスも同じに変わる) | そのまま当てる | する (シェイプを共有) |
| UV が無い | 警告 (カット / 縫合しても変わらない) | そのまま | する |

トランスフォームだけのロック・リファレンスのメッシュはカットできる (旧版で確認) ので、知らせない。

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [utils/mesh.py](../utils/mesh.py) | `isShapeLocked()` (シェイプの `isLocked`)・`instanceCount()` (`instanceCount(False)`)・`uvCount()` (`numUVs`) |
| [tool/mesh_checks.py](../tool/mesh_checks.py) | `edit_blocker(mesh)` (カット / 縫合できない理由か None)・`report(mesh)` (知らせることをログに) |
| [tool/uv_apply.py](../tool/uv_apply.py) | `apply_guides` が `edit_blocker` を見て飛ばす (ツールのボタン・キー・api の `cut_guides` のどれも通る) |
| [tool/guide_storage.py](../tool/guide_storage.py) | ロックされたシェイプには書かない (編集のたびの警告を出さない) |
| [tool/context.py](../tool/context.py) | 対象にしたとき (ツールを有効にしたとき・選んで加えたとき) に `report` |

## 仕組み

- **前もって調べる**: ロックされたシェイプに polyMapCut を当てると失敗し、Maya のエラーからは理由が分かりにくい。
  当てる前に `edit_blocker` で調べて、理由を出す
- **知らせるのは 1 回だけ**: 対象にしたときに `report` で知らせ、そのあとの保存では警告しない (ロックしたメッシュでも
  ガイドは作れて、ツールの中には残る。シーンには保存されない)

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); cmds.instance("pSphere1")          # インスタンス -> 知らせる
cmds.polyCube(); cmds.polyMapDel("pCube1")            # UV なし -> 警告
cmds.polyPlane(); cmds.lockNode("pPlaneShape1")       # ロック -> 警告、カットは飛ばす
cmds.select("pSphere1", "pCube1", "pPlane1"); UVSeamTool.tool()
```

mayapy (2027) で、それぞれの判定・ログ・ロックしたメッシュのカットが飛ばされること (0 本) を確かめた。
