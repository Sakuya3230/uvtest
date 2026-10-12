# 段階 2: 対象のメッシュとエッジの選択モード

[目次](README.md) ・ 前: [段階 1](01_settings.md)

## 目的

- ツールを有効にしたとき、選んでいるメッシュを対象にする
- 対象をエッジの選択モードにする (頂点 / エッジのどちらを拾うモードでも共通。確定したエッジを
  選択として残すため)
- メッシュを選んでいなければ警告を出す

## 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [scene/mesh.py:32](../scene/mesh.py#L32) `mesh_shape` | 名前 (Transform かシェイプ) から、表示されているメッシュのシェイプ。中間オブジェクトは飛ばす |
| [scene/mesh.py:49](../scene/mesh.py#L49) `target_mesh` | 選択 → ハイライトの順に、最初のメッシュのシェイプ |
| [scene/mesh.py:64](../scene/mesh.py#L64) `shape_transform` | シェイプの親の Transform |
| [scene/mesh.py:70](../scene/mesh.py#L70) `enter_edge_mode` | エッジの選択モードにする (マーキングメニューの「エッジ」と同じことを cmds で) |
| [scene/mesh.py:90](../scene/mesh.py#L90) `mesh_counts` | 頂点・エッジ・フェースの数 |
| [scene/mesh.py:25](../scene/mesh.py#L25) `dag_path` | 名前の MDagPath |
| [tool/context.py:61](../tool/context.py#L61) `toolOnSetup` | 対象を決め、エッジの選択モードにし、数をログに出す。無ければ警告 |
| [tool/context.py:74](../tool/context.py#L74) `toolOffCleanup` | 対象を忘れる |
| [reloader.py](../reloader.py) | `UVPathCut.scene.mesh` を `MAYA_MODULES` に足した |
| [tests/UVPathCut/mayapy/test_mesh.py](../../tests/UVPathCut/mayapy/test_mesh.py) | 対象の決め方 (mayapy 6 件) |

## 仕組み

### 対象の決め方

```
target_mesh()
  1. cmds.ls(selection=True, objectsOnly=True)   選んでいるもの
       - オブジェクト (Transform / シェイプ) ならその名前
       - コンポーネント ("box.e[2]") なら、そのシェイプの名前 (objectsOnly の働き)
  2. cmds.ls(hilite=True)                        何も選んでいなければ、ハイライトしているもの
  -> それぞれ mesh_shape() で、表示されているメッシュのシェイプにして、最初のもの
```

`mesh_shape` は、Transform なら `listRelatives(shapes=True, type="mesh", noIntermediate=True)` の
最初のもの、シェイプなら中間オブジェクトでないことを確かめてそのまま返す。

### 中間オブジェクト

スキンやブレンドシェイプを付けると、Transform の下に **変形の元の形** のシェイプ
(`intermediateObject` が True。`boxShapeOrig` など) ができる。見えないので対象にしない。

### エッジの選択モード

Maya の選択には 2 つのモードがある。

| モード | 意味 | エッジにする方法 |
|---|---|---|
| オブジェクトの選択モード | 普段のモード。ハイライトしたオブジェクトだけコンポーネントを選べる | ハイライトしたオブジェクト用のマスク (`selectType -objectComponent`) をエッジだけにして、`hilite` |
| コンポーネントの選択モード | F8 で入るモード | マスク (`selectType`) をエッジだけにして、`hilite` |

右クリックのマーキングメニューの「エッジ」は MEL の `doMenuComponentSelection` だが、
マーキングメニューを一度も使っていないと読み込まれていない。そこで同じことを cmds で行う。

## 落とし穴

- `doMenuComponentSelection` を直接呼ぶと「Cannot find procedure」になることがある (ウェイトスライダーで確認)
- 選択のモード・マスクは GUI の状態なので、mayapy では切り替えても残らない。エッジの選択モードは GUI で確かめる
- 名前は `long=True` / `fullPath=True` のフルパスで扱う (同じ名前のノードが別の階層にあっても取り違えない)

## 試し方

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polySphere()
import UVPathCut; UVPathCut.tool()
# 球がエッジの選択モードになり、「対象 |pSphere1|pSphereShape1 (頂点 382 / エッジ 780 / フェース 400)」

cmds.select(clear=True)
UVPathCut.reload_modules(); UVPathCut.tool()   # 「メッシュを選んでからツールにしてください」(黄色)
```
