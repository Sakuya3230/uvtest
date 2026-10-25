# 段階 13: UV の切れ目の見え方

## 目的

ガイドが通るエッジのうち、もう UV の切れ目になっているもの (カット済み・メッシュの縁) を見えるようにする。

**ガイドは状態を持たない** (仕様のとおり。ユーザーが改めて選んだ)。カット済みかどうかは、描くたびに今の UV から求める。
状態を持たせると、ほかのツールで切った・縫った・カットを Undo した・ガイドを動かしたあとに、持っている状態が
実際の UV とずれるため。

| 見え方 | 意味 |
|---|---|
| ガイドの線のその部分が赤 (設定 `cutColor` = 「カットしたエッジ」) | そのエッジは UV の切れ目 (カット済み、またはメッシュの縁) |
| 普通の色 | 切れ目ではない (まだカットしていない、または縫合済み。UV の上では同じなので見分けない) |

旧版と同じ赤い線 (最初は線の下に太い縁取りを描いたが、派手なので変えた)。
選んでいる (橙)・マウスの下のガイドは、どれを指しているかが見えるよう、切れ目の部分も選択の色のまま描く。

## 仕組み

```
UV の切れ目 (core/seam/uv_seams.uv_seam_mask。numpy だけ)
  面ごとの頂点 (getVertices) と、角ごとの UV の番号 (getAssignedUVs) を、それぞれまとめて読む
  角 -> 同じ面の次の角 をエッジにし、小さい頂点 -> 大きい頂点 の向きにそろえて (UV も合わせて) 並べ替える
  同じエッジが 2 回出て、両端の UV の番号が違えば切れ目。1 回しか出ないエッジ (縁) も切れ目
  -> エッジごとの bool の配列
TargetMesh が持ち、外部の変更の知らせで求め直す
  sync() は、つながり・位置が同じで切れ目だけが変わったら UV を返す (カット / 縫合・その Undo)
  -> コンテキストは描き直すだけ (グラフは同じなので、サブツールには知らせない)
描く (tool/guide_drawing.draw_guides)
  区間の頂点の列を、切れ目かどうかが同じエッジの続きに分け (_runs)、切れ目の続きは赤、ほかは役割の色で 1 回ずつ描く
```

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [core/seam/uv_seams.py](../core/seam/uv_seams.py) | `uv_seam_mask(edges, counts, connects, uv_counts, uv_ids)` |
| [utils/mesh.py](../utils/mesh.py) | `faceVertices()`・`assignedUVs()`。`connectionKey(face_vertices)` は読んだものを渡せる (2 回読まない) |
| [tool/target_mesh.py](../tool/target_mesh.py) | 切れ目の配列を持つ・`sync` が `UV` を返す・`isUVSeam(a, b)` |
| [tool/guide_drawing.py](../tool/guide_drawing.py) | 切れ目の部分を赤で描く (`_runs`) |
| [core/settings/definitions.py](../core/settings/definitions.py) | `cutColor` (カットしたエッジ。ツール設定のウィンドウの「色」の欄にも出る) |
| [tool/context.py](../tool/context.py) | `UV` の変更は描き直すだけ |

## 落とし穴

- 同じ所に 2 本の線を重ねて描くと、同じ奥行きでちらつく。切れ目の部分とそうでない部分に分けて、それぞれ 1 回だけ描く
- メッシュの縁も切れ目になる (UV の上では切れているため)。開いたメッシュの縁に沿ったガイドは、最初から赤い
- 見ているのは今の UV セットだけ

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()
# ガイドを作って確定 -> C (作成中なら作成中のガイド) / 編集で選んで C -> 選択を外すと、切った部分が赤い線
# Ctrl+Z (カットを戻す) -> 普通の色に戻る / S (縫合) -> 普通の色に戻る
```

mayapy (2022) で、平面の縁 (3x3 で 12 本) だけが切れ目・球のガイドの 20 本がカットの前は 0 本・後は 20 本・
Undo で 0 本に戻り、`sync` が `UV` を返すことを確かめた。
