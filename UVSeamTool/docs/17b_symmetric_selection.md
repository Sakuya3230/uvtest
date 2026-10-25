# 段階 17b: 選択のモードの対称の選択

## 目的

選択のモードで、対称が効いているとき (ツールの対称か Maya の対称。17a の `current_plane`) は、反対側のエッジも
一緒に光らせて選ぶ。Maya の `setAllowSymmetry` は使わない (選択を自前で作ったため。16b)。

| 操作 | 対称が効いているとき |
|---|---|
| マウスを乗せる | 光らせるエッジ (1 本かループ) の反対側も、薄い色で光らせる (設定 `mirrorColor`) |
| クリック・ダブルクリック・ループの事前ハイライト | 光っているエッジと、その反対側を一緒に選ぶ (修飾キーの決まりは同じ) |
| 矩形 | 矩形に入ったエッジと、その反対側を一緒に選ぶ |

反対側が見つからないエッジは、片側だけを選ぶ。どの操作も 1 回の `cmds.select` (1 回の Undo)。

## 仕組み

```
光らせる -> SelectTool.draw: 光るエッジ (loopColor / hoverEdgeColor) + _mirror_only (反対側のうち、まだ無いもの。mirrorColor)
クリック・ダブルクリック -> select_edges([(メッシュ, _with_mirror(エッジ))], 選び方)
矩形 -> SelectTool._select_in_rect
          utils.selection.edges_in_rect     Maya の矩形選択 (selectFromScreen) で矩形に入るエッジを求め、選択はすぐ元に戻す
          対象のメッシュなら _with_mirror で反対側を足す
          select_edges(全メッシュ, 選び方)   1 回の cmds.select。置き換えで何も無ければ選択を外す
```

矩形は 16b では「selectFromScreen で選んでから cmds.select で書き直す」だったが、反対側を足すために
「矩形に入るエッジを求めるだけ (選択は戻す) -> 反対側を足す -> 選び方で選ぶ」に変えた。Shift (切り替え) や
Ctrl (外す) でも、両側が同じように変わる。

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [utils/selection.py](../utils/selection.py) | `select_edges(items, 選び方)` (複数のメッシュを 1 回の cmds.select で)・`edges_in_rect(rect)` (`select_in_rect` から変えた) |
| [tool/select_tool.py](../tool/select_tool.py) | 反対側を光らせる・足して選ぶ (`_mirror_only` / `_with_mirror`)・`_select_in_rect` |
| [core/settings/definitions.py](../core/settings/definitions.py) | `mirrorColor` (反対側 (対称)) |

## 落とし穴

- 反対側は対応表 (17a) で決めるので、形が左右でずれていると見つからない (その分は片側だけ。対称をオンにしたときに数をログに出す)
- 矩形の `edges_in_rect` は、Maya の選択を一度変えて戻す (Undo には積まれない)

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()
# X (対称) -> [選択] -> マウスの下のエッジと反対側が光る -> クリックで両側 / ダブルクリックで両側のループ / 矩形
# Ctrl+クリックで両側を外す / C でカット (両側)
```

mayapy で、対称がオフなら片側だけ・オンならクリックで両側 (反対側は対応表のとおり)・Ctrl で両側を外す・ダブルクリックで
両側のループ (経線 20 本 + 反対側 20 本)・1 回の Undo で戻ることを確かめた (矩形の selectFromScreen は GUI で)。
