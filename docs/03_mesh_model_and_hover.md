# 段階 3: MeshModel とマウスの下の面

[目次](README.md) ・ 前: [段階 2](02_target_mesh.md)

## 目的

- 対象のメッシュの状態を **`MeshModel`** にまとめる (MFnMesh の使い回しと作り直し。後の段階で
  グラフ・外部の変更の検知・対称の対応表もここに足す)
- マニピュレータでマウスの移動を受け取り、マウスの下の **表の面** を求めて描く
- 旧版で GUI のクラッシュになった「カットしたあとに古い MFnMesh を使うと落ちる」問題を、
  最初から起きない形にする

## 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/geometry.py](../core/geometry.py) | `fan_triangles` (多角形を三角形に) / `toward` (点を目へ寄せる) / `midpoint` / `distance` |
| [core/picking.py](../core/picking.py) `FaceHit` | 当たった面 (番号・交点・角の頂点と位置・表か)。座標はタプル |
| [scene/mesh.py:106](../scene/mesh.py#L106) `MeshModel` | 対象のメッシュの状態 |
| [scene/mesh.py:140](../scene/mesh.py#L140) `fn` | MFnMesh (dirty なら作り直す。索引と MItMeshPolygon も) |
| [scene/mesh.py:128](../scene/mesh.py#L128) `_on_dirty` / [:133](../scene/mesh.py#L133) `release` | dirty の通知で捨てる / コールバックを外す |
| [scene/mesh.py:155](../scene/mesh.py#L155) `face_edges` | 面の辺 (番号と両端) |
| [scene/mesh.py:165](../scene/mesh.py#L165) `hit` | レイが当たる表の面 (`allIntersections`)。`front_only=False` なら最初の面 |
| [tool/drawing.py:28](../tool/drawing.py#L28) `view_ray` | ピクセルを通るワールドのレイ |
| [tool/drawing.py:49](../tool/drawing.py#L49) `display_color` | カラーマネジメントの逆変換 (画面にその色で見せる値) |
| [tool/manipulator.py:42](../tool/manipulator.py#L42) `UVPathManip` | マニピュレータ。[postConstructor:58](../tool/manipulator.py#L58) で `registerForMouseMove` |
| [tool/manipulator.py:71](../tool/manipulator.py#L71) `doMove` | マウスの下の面を求め、変わったら描き直す |
| [tool/manipulator.py:87](../tool/manipulator.py#L87) `preDrawUI` / [:97](../tool/manipulator.py#L97) `drawUI` | カメラを読む / 面の塗り・縁・番号を描く |
| [tool/context.py:78](../tool/context.py#L78) | `toolOnSetup` で `MeshModel` を作り、[_create_manipulator:91](../tool/context.py#L91) でマニピュレータを作る |
| [tool/context.py:81](../tool/context.py#L81) `toolOffCleanup` | マニピュレータを消し、`MeshModel` のコールバックを外す |
| [plug-ins/uvPathCut.py:66](../../../plug-ins/uvPathCut.py#L66) | マニピュレータのノードを登録 (creator は [_create_manip:45](../../../plug-ins/uvPathCut.py#L45)。クラスを毎回引く) |
| [constants.py](../constants.py) | `MANIP_NODE` / `MANIP_TYPE_ID` |
| [tests/UVPathCut/test_geometry.py](../../tests/UVPathCut/test_geometry.py) | 三角形への分け方など (pytest 3 件) |
| [tests/UVPathCut/mayapy/test_mesh.py](../../tests/UVPathCut/mayapy/test_mesh.py) | `MeshModel`: 表・裏・外れ / 手前の裏面を飛ばす / 面の辺 / カットのあとも落ちない (mayapy 4 件) |

## 仕組み

### マウスの移動を受け取る (マニピュレータ)

`MPxContext` (API 2.0) にはマウスの **移動** のイベントが無い (押す・ドラッグ・離すだけ)。
マニピュレータの `registerForMouseMove()` を呼んでおくと、マウスを動かすたびに `doMove` が呼ばれる。

```
コンテキスト.toolOnSetup
  -> UVPathManip.newManipulator("uvPathCutManip")  (Python のインスタンス, MObject)
       プラグインの creator (_create_manip) が、tool/manipulator.py の今のクラスで作る
  -> addManipulator(MObject)                        コンテキストに付ける
  -> manip.setModel(MeshModel)                      値を渡す (段階 14 から setTargets)
マウスを動かす
  -> UVPathManip.doMove(view)
       mousePosition() -> view_ray() -> MeshModel.hit() -> 面が変わったら view.refresh()
描き直し
  -> preDrawUI(view)     カメラの位置とカラーマネジメントの設定を読む
  -> drawUI(drawMgr)     面を描く
```

- マニピュレータは普通プラグにつないで値を動かすが、このツールはつながない。プラグが無いと
  `finishAddingManips` は kFailure になるので、`connectToDependNode` / `finishAddingManips` は呼ばない
- 描くものはすべて `kNonSelectable` なので、クリックは普通の選択のまま (押せる部品は段階 10)

### レイと交点

1. `view.viewToWorld(x, y, source, direction)` でマウスのピクセルを通るワールドのレイ
   (結果は渡した変数に書かれる)
2. `MFnMesh.allIntersections(..., sortHits=True)` で、レイが当たる面を近い順に全部
3. 面の法線とレイの向きの内積が負 (向き合っている) なら表の面。最初の表の面を使う

裏の面を飛ばすので、閉じたメッシュでは見たとおりの面だけが選ばれ、開いたメッシュの裏側からは
奥の表の面を拾う (無ければ何も拾わない)。索引 (`autoUniformGridParams`) は MFnMesh に
キャッシュされるので、MFnMesh を使い回すと 2 回目からが速い。

### MeshModel と「使えなくなる MFnMesh」

MFnMesh は「そのときのメッシュのデータ」を指している。ヒストリーのあるメッシュを
`polyMapCut` などで変えるとデータが作り直され、前に作った MFnMesh を使うと Maya が落ちる。

```
MeshModel
  ├─ addNodeDirtyCallback(シェイプ) ─ dirty が届いたら MFnMesh / MItMeshPolygon / 索引を捨てる
  └─ fn プロパティ ─ 捨てていたら、ここで作り直す (使う直前)
```

カットでは dirty が 4 回、Undo では 6 回届く (旧版で確認)。届くたびに作り直すのではなく、
捨てるだけにして **次に使うときに 1 回だけ** 作り直す。

### 描画

- 面に重ねて描くと、奥行きの比べ合いで面に負けてちらつく。描く点をカメラへ距離の 0.2%
  寄せる (`toward`)。寄せる量を距離に比例させるので、遠くでも近くでも効く
- 色はカラーマネジメントの変換を通る。表示の色から逆算した値を渡す (`display_color`)。
  文字の色は変換されないので、そのまま渡す
- 多角形は扇形に三角形へ分けて塗る (`fan_triangles`)

## 落とし穴

- **ヒストリーのあるメッシュを polyMapCut したあと、前に作った MFnMesh を使うと Maya が落ちる**
  (getPoint でも)。ヒストリーの無いメッシュでは落ちない。古いものを捨てるだけなら落ちない。
  テスト `case_model_after_cut_does_not_crash` で、カット・Undo・Redo のあとも使えることを確かめている
- `MItMeshPolygon` などのイテレーターは、渡した MDagPath の参照を保持しない。一時オブジェクトを
  渡すと中身が壊れるので、MDagPath は `MeshModel` が持ち続ける
- `closestIntersection` は裏の面にも当たる。表の面だけを使うには `allIntersections` で近い順に調べる
- `doMove` の `refresh` 引数は Python からは書き戻せない。描き直すときは `view.refresh(False, True)`
- コールバックは必ず `release` で外す。外さないとツールを抜けても呼ばれ続け、リロードしたあとは
  古いコードが呼ばれる

## 試し方

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polySphere()
import UVPathCut; UVPathCut.tool()
# マウスを球の上で動かすと、下の面が緑で塗られて f[番号] が出る。球の外では消える

# リロードのあとも新しいコードのマニピュレータになるか (段階 3 で初めて確かめること):
# manipulator.py の COLOR_FACE_FRONT を (1, 0.5, 0) に変えて保存してから
r.reload().reload_modules(); UVPathCut.tool()          # 面が橙になれば、プラグインを読み直さずに反映できている
```
