# 段階 17a: 対称の対応表と設定

## 目的

対称 (17b: 選択のモード / 17c: ガイドの相手) の土台。反対側の頂点・エッジを求める対応表と、対称の設定・ボタン・キー。
この段階では、まだ反対側を使う機能は無い (対称をオンにしたとき、見つからない頂点をログに出すまで)。

## 決めたこと (ユーザーの選択)

- ガイドの対称は **相手のガイドを作る** (17c。どちらを編集しても相手を作り直す。SeamGuide と同じ)
- 対称の面は **ツールの設定 + Maya 優先**: Maya の対称がオン (ワールド / オブジェクト) なら Maya の面 (ツールの「対称」が
  オフでも効く)。そうでなければ、ツールの「対称」がオンのときだけツールの面 (旧版と同じ)
- 選択のモードの対称の選択は自前で作る (Maya の `setAllowSymmetry` は使わない。16b)

| 設定 | 既定 | 中身 |
|---|---|---|
| `symmetry` 対称 | オフ | ツールの対称 (パネルの「対称」・X キーで切り替え) |
| `mirrorSpace` 空間 | オブジェクト | オブジェクト / ワールド |
| `mirrorAxis` 軸 | X | X / Y / Z (その軸の成分の符号を反対にした位置が反対側) |
| `mirrorTolerance` 許容値 | 0.1 | 鏡に写した位置から、この距離の中でいちばん近い頂点を反対側にする |

Maya の対称がオンの間は、ツール設定のウィンドウの空間・軸・許容値を灰色にし、「Maya の対称: ワールド Y (許容値 0.1)。
こちらが優先されます」と見せる。パネルの「対称」は、ツールか Maya のどちらかの対称が効いていれば押された見た目。

## 仕組み

```
反対側 (core/symmetry/mirror_map.MirrorMap)
  頂点: 位置の軸の成分の符号を反対にした点に、cKDTree でいちばん近い頂点 (許容値より遠ければ -1。面の上の頂点は自分)
  エッジ: 両端の反対側の組を (小さい番号, 大きい番号) の 1 つの整数の鍵にし、元のエッジの鍵を並べた中から searchsorted で探す
          (辞書を作って 1 本ずつ引くより速い。旧版で 9 万エッジ 60 ms -> 速くなった方法)
今の対称の面 (tool/symmetry.current_plane)
  Maya の対称 (utils/symmetry.maya_symmetry) がオンで ワールド / オブジェクト -> Maya の面 (from_maya)
  そうでなく、ツールの「対称」がオン -> ツールの設定の面
  どちらでもない -> None (対称なし)
対応表の使い回し (TargetMesh.mirrorMap(plane))
  (空間, 軸, 許容値) ごとに作って覚える。位置・トポロジーが変わったら捨てる (反対側は位置で決めるため)
  初めて作ったとき、反対側が見つからない頂点があれば警告
```

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [core/symmetry/mirror_map.py](../core/symmetry/mirror_map.py) | `MirrorMap(位置, エッジ, 軸, 許容値)`・`vertex` / `edge` / `edges` / `unmatchedVertexCount` |
| [compat/accel.py](../compat/accel.py) | `spatial` (scipy.spatial。cKDTree) |
| [core/settings/setting.py](../core/settings/setting.py) | 種類 `BOOL` / `CHOICE` / `FLOAT`、`choices`・`minimum` / `maximum` |
| [core/settings/settings.py](../core/settings/settings.py) | `normalize` が新しい種類を直す (選択肢に無い値は ValueError、数は範囲に寄せる) |
| [core/settings/definitions.py](../core/settings/definitions.py) | 対称の 4 項目 (欄「対称」) |
| [utils/symmetry.py](../utils/symmetry.py) | `maya_symmetry()`: (空間, 軸, 許容値) か None (オフ・トポロジー) |
| [tool/symmetry.py](../tool/symmetry.py) | `MirrorPlane`・`current_plane()`・`describe(plane)` |
| [tool/target_mesh.py](../tool/target_mesh.py) | `mirrorMap(plane)` (面ごとに覚える) |
| [tool/setting_controls.py](../tool/setting_controls.py) | 設定の種類ごとの部品 (作る・コマンド・値を入れる・読む・灰色にする)。ウィンドウから分けた |
| [tool/tool_settings_window.py](../tool/tool_settings_window.py) | 欄「対称」・Maya の対称の表示と灰色 |
| [tool/actions.py](../tool/actions.py) / [tool/context.py](../tool/context.py) / [ui/icons.py](../ui/icons.py) | ボタン「対称」・X キー・アイコン (点線の軸と向き合う三角形)・設定が変わったらログと対応表 |

## 落とし穴

- Maya の対称の空間が「トポロジー」のときは、ツールの設定を使う (位置で決める対応表とは考え方が違うため)
- Maya の対称の切り替えは見張っていない。パネルの「対称」の見た目・ウィンドウの表示は、次にボタン・設定を変えたときに追い付く
- 許容値は 0.0001〜10 に寄せる

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()
# X -> 「対称 X」とログ。パネルの「対称」が押された見た目 / ツール設定のウィンドウの欄「対称」で軸・許容値
cmds.move(0.3, 0, 0, "pSphere1.vtx[3]", r=True)   # 形を左右でずらす -> 次に X で「反対側が見つからない頂点が 2 個」
cmds.symmetricModelling(symmetry=1, about="world", axis="y")   # Maya の対称 -> ウィンドウの空間・軸・許容値が灰色
```

mayapy (2022 / 2027) で、球の反対側の頂点・エッジ・見つからない数 (形をずらすと 2 個)・対応表の使い回しと位置が変わったら
作り直す・今の対称の面 (オフ / ツール / Maya / Maya をオフにするとツール)・設定の新しい種類の直し方を確かめた
(ツール設定のウィンドウとボタンは GUI で)。
