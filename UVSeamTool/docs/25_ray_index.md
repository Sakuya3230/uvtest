# 段階 25: レイの索引 (accelParams)

## 目的

マウスを動かすたびに、対象のメッシュすべてにレイを当てて (`MFnMesh.allIntersections`) マウスの下の頂点・面を拾っている。
索引なしだと面の数に比例して遅く、大きいメッシュ・多いメッシュでホバーが重くなる ([02b](02b_preview.md)・[10](10_multiple_meshes.md)・
[11](11_front_faces.md) に「後で」と残していたもの)。索引 (accelParams) を作って使い回す。

## 実測 (球、mayapy。1 回のレイ)

| 面の数 | 索引なし (2027 / 2022) | 索引を作る最初の 1 回 | 索引あり |
|---|---|---|---|
| 2,500 | 0.16 / 0.69 ms | 1〜2 ms | 0.01〜0.05 ms |
| 24,000 | 1.5 / 1.4 ms | 6〜8 ms | 0.01〜0.05 ms |
| 240,000 | 16 / 15 ms | 37〜48 ms | 0.01 ms ほど |

ツールの中の `pick_vertex` (24 万面): 最初 48〜66 ms、2 回目から 0.03〜0.04 ms。

## 仕組み

```
Mesh.rayMeshFn()      (MFnMesh, autoUniformGridParams()) を初めて使うときに作り、Mesh が持ち続ける
picking._front_hit    rayMeshFn の MFnMesh と accelParams で allIntersections (表の面の判定などもその MFnMesh で)
MeshWatcher._on_dirty シェイプ・親に dirty が届いたその場で Mesh.resetRayIndex() (次のレイで作り直す。下の落とし穴)
TargetMesh.sync       つながり・位置が変わったら Mesh.resetRayIndex() (念のため)
```

- **索引は MFnMesh の中に作られる**。毎回 `om.MFnMesh(path)` を作ると、索引も毎回作り直しになる (かえって遅い) ので、
  同じ MFnMesh を持ち続ける
- 当てるのはワールド空間。トランスフォームを動かしただけなら、索引を捨てる前でも新しい位置に当たった (mayapy で確認)。
  形を変えたとき (変形・頂点の移動・トポロジー) のために、sync で捨てる
- UV だけの変更 (カット / 縫合) では捨てない (形は変わらない)

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [utils/mesh.py](../utils/mesh.py) | `rayMeshFn`・`resetRayIndex` |
| [utils/picking.py](../utils/picking.py) | `_front_hit(mesh, ...)` が索引を使う |
| [utils/mesh_watcher.py](../utils/mesh_watcher.py) | dirty を受けたその場で索引を捨てる (Maya が落ちないように) |
| [tool/target_mesh.py](../tool/target_mesh.py) | `sync` で位置・つながりが変わったら索引を捨てる |

## 落とし穴

- **メッシュが作り直されたあとに、持ち続けた古い MFnMesh に触ると Maya が落ちる** (access violation)。最初は
  `TargetMesh.sync` (手すきのときに 1 回) で捨てていたが、自動のカットで 2 つ目の点を置いた直後に落ちた
  (`polyMapCut` でメッシュが作り直され、sync の前のマウスの移動で古い MFnMesh にレイを当てた)。mayapy でも
  「MFnMesh を持つ -> polyMapCut -> allIntersections」で再現した。そこで **`MeshWatcher` が dirty を受けたその場で
  `Mesh.resetRayIndex()`** するようにした (カット・Undo・スムーズのあとも落ちず、正しい頂点を拾うことを確かめた)
- そのため、ガイドの編集 (シェイプのアトリビュートに書く) でも dirty が届いて索引を捨てる。次のレイで作り直す (24 万面で 40〜60 ms)
- 最初の 1 回は索引を作る分だけ遅い (24 万面で 40〜60 ms)。マウスを最初に乗せたときに 1 回だけ
