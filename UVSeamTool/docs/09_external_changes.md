# 段階 9: 外部の変更の検知

## 目的

ツールを使っている間に、メッシュを外から変えられても (動かす・変形する・トポロジーを変える・消す)、描画と拾い方が
ずれないようにする。

| 変更 | どうするか |
|---|---|
| メッシュ・親を動かす / 変形 | 描画用の位置とグラフ (エッジの長さ) を読み直す。ガイドはそのまま |
| トポロジーが変わる | 全部を読み直し、保存したガイドも読み直す (トポロジーが違えば使わない = 段階 6 の決まり)。Undo でトポロジーを戻せば、ガイドも戻る |
| メッシュを消す | 警告して、ツールを抜ける |
| UV だけが変わる (カット / 縫合)・ガイドの保存 | 位置もつながりも同じなので、何もしない |

## 流れ

```
Maya がシェイプ / 親のトランスフォームを dirty にする・シェイプを消す
  -> MeshWatcher._on_dirty (utils)         何度届いても、最初の 1 回だけ executeDeferred に予約
  -> (手すきのとき) Context._on_mesh_changed
       メッシュが消えた -> 警告して selectSuperContext に
       TargetMesh.sync()
         面ごとの頂点の並びのハッシュ (Mesh.connectionKey) が違う -> 全部を読み直し、ガイドも読み直す (TOPOLOGY)
         位置 (オブジェクト / ワールド) が違う                     -> 位置とグラフだけ (MOVED)
         どれも同じ                                                -> UNCHANGED (何もしない)
       変わっていれば、サブツールの targetChanged() -> 描き直し
```

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [utils/mesh_watcher.py](../utils/mesh_watcher.py) | `MeshWatcher(mesh, on_change)`: シェイプと親たちの dirty・シェイプの削除を見て、手すきのときに 1 回呼ぶ。`release()` |
| [utils/mesh.py](../utils/mesh.py) | `connectionKey()`: `getVertices` (面ごとの頂点の数と並び) のハッシュ |
| [tool/target_mesh.py](../tool/target_mesh.py) | `sync()` (UNCHANGED / MOVED / TOPOLOGY)。読み込みを `_read_all` にまとめた |
| [tool/sub_tool.py](../tool/sub_tool.py) | `targetChanged()` (既定: `cancel` + `refresh`) |
| [tool/create_tool.py](../tool/create_tool.py) | `targetChanged`: 前のグラフの PathTree を捨てる |
| [tool/guide_edit.py](../tool/guide_edit.py) | 編集したときのトポロジーを覚え、Undo はアトリビュートの文字列をそのまま書き戻す |
| [tool/guide_storage.py](../tool/guide_storage.py) | `save_text(mesh, 文字列)` (None ならアトリビュートを消す) |
| [tool/context.py](../tool/context.py) | ウォッチャーを付ける / 外す・`_on_mesh_changed` |

## 仕組み

- **予約して 1 回だけ**: ドラッグで動かしている間などは dirty が何度も届く。届くたびに読み直さず、最初の 1 回で
  `executeDeferred` に予約し、手すきのときにまとめて 1 回だけ読み直す
- **親も見る**: 親のトランスフォームを動かしても、シェイプには dirty が届かない。シェイプからワールドまで親をたどって、
  それぞれにコールバックを付ける
- **つながりは安く確かめる**: エッジは 1 本ずつしか読めず遅い。`getVertices` (全部の面をまとめて読める) のハッシュで
  比べ、違うときだけエッジを読み直す
- **トポロジーが変わったあとの Undo**: 前のトポロジーのときの編集を Undo / Redo しても、写し (guide_store) は変えない
  (古い頂点の番号のガイドが新しいメッシュに出るため)。アトリビュートだけを書き戻す
- **Undo はアトリビュートの文字列をそのまま戻す**: 写しから作り直すと、トポロジーが違って使っていなかったガイドが
  失われる (トポロジーを変えたあと、新しいガイドを作って Undo すると、元のガイドの文字列が戻らなかった。mayapy で確認して直した)

## 落とし穴

- コールバックは `toolOffCleanup` で必ず外す (外さないと、ツールを抜けても・リロードしたあとも古いコードが呼ばれる)
- ガイドを保存する (アトリビュートに書く) と、シェイプの dirty が届いて確かめが走る (何も変わっていないので何もしない)
- 親を付け替える (ペアレント) と、見ている親が変わる。今は見直さない (ツールに入り直せば見直す)
- standalone (mayapy) では executeDeferred の予約が実行されないので、予約まで届くことを確かめた (実行は GUI で)

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()
# ガイドを作る -> 移動ツールに替えずに、チャンネルボックスで translateX を変える -> ガイドが付いてくる
# スクリプトエディタで cmds.polySmooth("pSphere1") -> 「トポロジーが変わった」・ガイドが消える -> Ctrl+Z -> 戻る
# cmds.delete("pSphere1") -> 警告してツールを抜ける
```

mayapy (2022 / 2027) で、親・頂点を動かしたときの予約と読み直し (MOVED)・カットでは UNCHANGED・
トポロジーを変えて読み直し (TOPOLOGY)・トポロジーを変えたあとの編集の Undo とスムーズの Undo で元のガイドが戻ること・
コールバックを外したあとは呼ばれないこと・消したメッシュが無効になることを確かめた。
