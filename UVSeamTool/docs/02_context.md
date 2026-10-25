# 段階 2a: コンテキストとクリックで点を足す

## 目的

段階 1 の核を、ビューのクリックで動かす。描画はまだ無い (ログで確かめる)。プレビューの描画は段階 2b。

| 操作 | 動き |
|---|---|
| 左クリック (メッシュの上) | マウスの下の頂点に点を足す (2 つ目からは前の点から最短パスで区間を求める) |
| Delete / Backspace | 最後の点を消す |
| Enter | 作成中のガイドでカットして終える |
| Esc | 作成中のガイドを捨てる |
| メッシュの外・Shift / Ctrl 付きのクリック | Maya の普通の選択 |

## 流れ

```
UVSeamTool.tool()                                     api.py: プラグインを読み込み、コンテキストを作って setToolTo
  -> UVSeamToolContext.toolOnSetup                     tool/context.py: 選んだメッシュで CreateTool を作る
左クリック
  -> UVSeamToolContext.doPress                         受け取るかどうかをサブツールに聞くだけ
     -> CreateTool.press                               tool/create_tool.py
        -> picking.vertex_under_cursor (utils)         レイが当たった面の、いちばん近い頂点
        -> GuideCreation.addVertex (core)              editing.new_guide / add_point
Enter
  -> UVSeamToolContext.completeAction -> CreateTool.complete
        -> seam_edges (core) -> uv_editor.cut_edges (utils)
```

## 追加したもの

| ファイル | 中身 |
|---|---|
| [plug-ins/uvSeamTool.py](../../../plug-ins/uvSeamTool.py) | 登録だけ。creator がコマンドのクラスを毎回 importlib で引く |
| [constants.py](../constants.py) | `PLUGIN_NAME` / `CONTEXT_COMMAND` / `CONTEXT_NAME` |
| [api.py](../api.py) | `tool()`・`load_plugin()` |
| [tool/context_command.py](../tool/context_command.py) | `UVSeamToolContextCommand` (makeObj でコンテキストを作る)・`delete_tool_context()` |
| [tool/context.py](../tool/context.py) | `UVSeamToolContext`: マウスとキー (Enter / Esc / Delete) をサブツールへ渡すだけ |
| [tool/sub_tool.py](../tool/sub_tool.py) | `SubTool`: サブツールの入り口 (press / drag / release / complete / abort / delete) |
| [tool/create_tool.py](../tool/create_tool.py) | `CreateTool`: ガイドを作るサブツール |
| [core/guide/guide_creation.py](../core/guide/guide_creation.py) | `GuideCreation`: 作成中のガイド (点を足す・最後の点を消す・捨てる)。Maya に触らない |
| [utils/picking.py](../utils/picking.py) | `vertex_under_cursor(mesh, x, y)` |
| [reloader.py](../reloader.py) | 読み直す前にコンテキストを消す |

## 仕組み

- **コンテキストは判断しない**: `doPress` はサブツールの `press` が True を返したか (受け取ったか) だけを見る。
  False なら基底の `doPress` (Maya の選択) を呼ぶ。押したときに受け取ったら、離すまでサブツールに渡す (`_consumed`)
- **Enter / Esc / Delete**: MPxContext の `completeAction` / `abortAction` / `deleteAction` が Maya から呼ばれる。
  キーのフィルターを自分で作らなくてよい
- **最後の点を消す**: `GuideCreation` は点を足す前のガイドを `_history` に積む。ガイドは変えられない値なので、
  前のガイドをそのまま戻すだけでよい
- **頂点を拾う**: `M3dView.viewToWorld` でビューのピクセルを通るレイを作り、`MFnMesh.closestIntersection` で当たった面の
  頂点のうち、当たった点にいちばん近いもの

## 落とし穴

- 基底の `toolOnSetup` / `toolOffCleanup` は呼ばない (API 2.0 では SystemError)
- 基底の `doPress` などは `omui.MPxSelectionContext.doPress(self, ...)` と明示して呼ぶ (段階 20 で基底を MPxContext に替え、基底へは渡さなくなった)
- コンテキストは作ったときのクラスのまま動く。リロードの前に消す (`reload_modules()` が消す)
- mayapy (standalone) ではコンテキストを作れない。ツールの動きは GUI で確かめる
- 裏の面にも当たる (closestIntersection は最初に当たった面)。必要になったら表の面だけにする

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere()
UVSeamTool.tool()
# 球の上を 3 か所クリック -> スクリプトエディタに「点を足しました: 頂点 ...」
# Delete で最後の点を消す / Enter でカット (UV エディタで切れ目を見る) / Esc で捨てる
```
