# 段階 14: エッジの選択モード

## 目的

ツールにしたとき・メッシュを対象に加えたときに、対象のメッシュをエッジの選択モード (ハイライトしてエッジだけを選べる
状態) にする (旧版と同じ)。前は選択モードを変えなかったので、カットしたときに Maya の選択がエッジに切り替わり、
選択の見え方が変わっていた。

## 変えたもの

| ファイル | 中身 |
|---|---|
| [utils/selection.py](../utils/selection.py) | `enter_edge_mode(meshes)` (旧版の `enter_edge_mode` と `_ensure_edge_mode` をまとめた) |
| [tool/context.py](../tool/context.py) | `toolOnSetup` の手順 2 と、選んで加えたとき (`_on_selection_changed`) に呼ぶ |

## 仕組み

- 右クリックのマーキングメニューの「エッジ」と同じことを cmds で行う。MEL の `doMenuComponentSelection` は、マーキング
  メニューを一度も使っていないと読み込まれていない (旧版で確認) ので使わない
  - オブジェクトの選択モード: ハイライトしたオブジェクト用のマスク (`objectComponent`) をエッジだけにして `hilite`
  - コンポーネントの選択モード: マスクをエッジだけにして `hilite`
- **Undo には積まない** (`undoInfo(stateWithoutFlush=False)` の間に行い、元の状態に戻す)。積むと、Ctrl+Z の 1 回目が
  ハイライトを戻すだけになり、ガイドの編集などの Undo が 1 回ずれる

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()     # 球がエッジの選択モードになる
# ガイドを作って C -> 選択モードは変わらない / Ctrl+Z -> カットが戻る (ハイライトの分のずれが無い)
cmds.polyCube()                           # 加えた立方体もエッジの選択モードになる
```

mayapy (2022 / 2027) で、ハイライトが付くこと・Undo の列が変わらず Undo の状態も元に戻ることを確かめた
(選択のマスクは standalone では問い合わせられないので GUI で)。
