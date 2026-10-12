# 2. メッシュと表示 (手順 4〜7)

[目次](README.md) ・ 前: [1. 土台](01_foundation.md) ・ 次: [3. パスと編集](03_path_and_edit.md)

## 手順 4: 対象のメッシュとエッジの選択モード

**ゴール**: ツールを有効にしたとき、選んでいるメッシュを対象にし、エッジの選択モードにする。

**方法**

- 対象は `cmds.ls(selection=True, objectsOnly=True, long=True)` (コンポーネントを選んでいてもシェイプが返る)、
  無ければ `cmds.ls(hilite=True)`
- Transform の下の**中間オブジェクト** (`intermediateObject`。スキンの元の形) は飛ばす
- エッジの選択モードは `selectType` / `hilite` で直接 (MEL の `doMenuComponentSelection` はマーキングメニューを
  使っていないと読み込まれておらず「Cannot find procedure」)
- ハイライトを付け直す処理を Undo に積まない (`undoInfo(stateWithoutFlush=False)` で囲む)。積むと Ctrl+Z が 1 回ずれる

**実装**: [scene/mesh.py](../../scene/mesh.py) `target_meshes` / `enter_edge_mode` / 記録 [02_target_mesh.md](../02_target_mesh.md)

## 手順 5: MeshModel とマウスの下の面

**ゴール**: マウスを動かすと、マウスの下の面を強調する。

**作るもの**: `scene/mesh.MeshModel` (メッシュの状態をまとめる)、マニピュレータ `tool/manipulator.UVPathManip`

**方法**

- **マウスの移動はマニピュレータで受け取る**。`MPxContext` には移動のイベントが無い。`MPxManipulatorNode` の
  `postConstructor` で `registerForMouseMove()` を呼ぶと、移動のたびに `doMove` が呼ばれる
  (押せる部品が 1 つも無くても呼ばれる)。プラグをつながないので `connectToDependNode` / `finishAddingManips` は呼ばない
- マウスの位置 -> レイ: `M3dView.viewToWorld(x, y, MPoint, MVector)` (結果は渡した変数に書かれる)
- レイ -> 面: `MFnMesh.allIntersections(..., sortHits=True)` で近い順。**表の面** (法線とレイが向き合う) の最初を使う
  (裏の面は拾わない)。交点の索引 `autoUniformGridParams()` は MFnMesh と一緒に使い回す
- **MFnMesh はメッシュが変わったら捨てる**: シェイプの dirty の通知 (`MNodeMessage.addNodeDirtyCallback`) で捨て、
  次に使うときに作り直す。ヒストリーのあるメッシュを polyMapCut したあとに古い MFnMesh を使うと **Maya が落ちる**
- メッシュが消えたかは `MObjectHandle.isValid()` (消したら描かない・拾わない。Undo で戻れば同じノード)
- `MItMeshPolygon` などは渡した MDagPath の参照を保持しないので、パスはモデルが持っておく

**確かめ方**: mayapy で `hit` (表 / 裏 / 外れ)、カットのあとも落ちないこと。GUI で面が強調されること。

**実装**: [scene/mesh.py](../../scene/mesh.py) `MeshModel`・[tool/manipulator.py](../../tool/manipulator.py) / 記録 [03_mesh_model_and_hover.md](../03_mesh_model_and_hover.md)

## 手順 6: 頂点 / エッジを拾う

**ゴール**: マウスに最も近い頂点 / エッジ (当たった面の角 / 辺) を強調する。

**方法**

- `core/picking.pick_component(hit, face_edges, mode, mouse, project)` を**純粋関数**にする。面の角 / 辺を画面に投影して
  (`project` は `M3dView.worldToView` を包んだ関数)、画面でマウスに最も近いもの
- 辺の両端は `getEdgeVertices` で読む (面の辺の並びと角の並びの対応に頼らない)
- 拾ったものが変わったときだけ描き直す (`view.refresh(False, True)`)

**確かめ方**: pytest で投影を差し替えて (平行投影の関数) 拾う。GUI で拾ったものが追従すること。

**実装**: [core/picking.py](../../core/picking.py) / 記録 [04_picking.md](../04_picking.md)

## 手順 7: 描画の一覧と描画

**ゴール**: 何を描くかを純粋な一覧 (DrawList) にし、描く関数は 1 つにする。

**方法**

- `core/draw_list`: 役割 (拾ったもの・パス・スタート・区間…) と見た目の表 `THEME` (色・太さ・手前に出す度合い)。
  `hover_items` / `path_items` などが一覧を作る (Maya に依存しない)
- `tool/drawing.render(drawMgr, 一覧, 目の位置, ...)`: マニピュレータの `drawUI(drawMgr, frameContext)` で描く。
  カメラは `preDrawUI(view)` で読む (`drawUI` には M3dView が来ない)
- メッシュに重ねる線・点は**カメラへ少し寄せる** (距離に比例。面とちらつかない)
- 色はカラーマネジメントの逆変換を通す (文字の色は変換されない)
- 色を設定にするときは「設定の色 -> 役割」の表 (`COLOR_ROLES`) を作り、`render` に渡す

**確かめ方**: pytest で一覧の中身。GUI で見た目。

**実装**: [core/draw_list.py](../../core/draw_list.py)・[tool/drawing.py](../../tool/drawing.py) / 記録 [06_draw_list.md](../06_draw_list.md)
