# 段階 27: 版 1 (最短だけ) と版 2 に分ける

段階 27 では SeamGuide の道具 (ライン・カーブ・フリーハンド・リング・谷・つなぎ線・付き方) を取り入れていた。ユーザーの指定で、
ここで 2 つのパッケージに分けた (2026-10-25):

| パッケージ | 中身 |
|---|---|
| `scripts/UVSeamTool` (版 1) | 最短パスのガイドだけ。段階 26 までの機能 + 段階 27 のうち最短で使えるもの (下の表) |
| `scripts/UVSeamTool2` (版 2) | 段階 27 の続き (開発はこちらで続ける)。段階 27a〜27k の解説は `UVSeamTool2/docs/` |

## 版 1 に取り込んだもの

| もの | 中身 |
|---|---|
| 点の持ち方 | `GuidePoint(vertex)` と `GuideSegment(mode, seam)` (版 2 の持ち方から表面の点・付き方・形を外した形。保存の形も版 2 の頂点の点と同じ書き方) |
| 点の挿入 | 選んだガイドの線のクリックで、シームの上のいちばん近い頂点に挿入 (`editing.insert_point`) |
| まとめて動かす | 選んでいる点 (つかんだ点も選択に足す) を、つかんだ点の移動量だけ動かして、いちばん近い頂点へ (`core/guide/group_drag.py`・`TargetMesh.nearestVertexTo`)。ドラッグは `tool/point_dragging.py` |
| 切り離す・接続する | マーキングメニューの下のリスト。選んだ点で切る / 2 本の端どうし (端の点を選べばその端) をつなぐ・1 本を閉じる。足す区間は最短 (`core/guide/split_join.py`) |
| 点の削除 | 前後の点を最短パスでつなぐ (`segment_modes.delete_point`。`segment_modes.py` は最短だけの求め直し) |

## 版 1 だけで足したもの

- カット / 縫合のあとの選択: `polyMapCut` / `polyMapSew` は終わると操作したエッジを選択に足すので、`utils/uv_editor.py` が呼ぶ前後で選択を元に戻す（`_keep_selection`。エッジを選ぶのはツールを抜けるときの `exit_selection` だけ）。テスト `test_cut_and_sew_keep_selection`
- 設定 `deleteGuideOnComplete`（確定後にガイドを削除。ユーザーの要望: 自動カットのあとは確定したガイドをいじらないことが多いため。`tool/create_tool.complete` が、確定と同時に `set_editing.remove_guides` で消す = 1 回の Undo で作成中に戻る。マーキングメニューの「自動 >」W にも）。テスト `test_delete_guide_on_complete`
- 設定 `lineWidth`（ガイドの線の太さ）と `pointSize`（点の大きさ）。ツール設定のウィンドウの「表示」。版 2 は実装メモだけ（[UVSeamTool2/docs/memo_display_sizes.md](../../UVSeamTool2/docs/memo_display_sizes.md)）

## 版 1 から外したもの (版 2 にある)

描き方 2〜7 (ライン・カーブ・フリーハンド・リング・谷・つなぎ線)、区間の作り方の切り替え (「区間 >」)、境界をガイドに、
付き方 (端をほかのガイドに乗せる)、リングの Ctrl / Shift+ホイール・断面に戻す、形のある区間の表示、表面に寄せる
(`utils/surface.py`・`Mesh.closestIntersector`)、設定 drawMethod / bridgeRoute / valleyStrength / shapeSeamColor /
attachedPointColor。

## 2 つの版を同じ Maya で使う

名前はすべて `constants.py` にあり、版 2 は `...2` にした (プラグイン `uvSeamTool2.py`・コマンド `uvSeamTool2Ctx` /
`uvSeamTool2Edit`・保存のアトリビュート `uvSeamTool2Guides`・設定ファイル `<一時フォルダ>/UVSeamTool2/settings.json`・
ログの環境変数 `UVSEAMTOOL2_LOG_LEVEL`)。両方のプラグインを同時に読み込めて、同じメッシュに両方のガイドを保存しても
互いに壊さない (版 2 は表面の点などを保存するので、版 1 では読めない)。設定ファイルに相手の版の項目があっても、知らない
項目は読み飛ばす。

## テスト

`scripts/tests/UVSeamTool` は版 1 の分 (core 16・scene 11・pytest 9)。版 2 のテストは `scripts/tests/UVSeamTool2`。

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()
# 最短でガイドを作る -> 編集で点を矩形で選んでドラッグ (まとめて) / 線をクリックで挿入 / 「切り離す」「接続する」
# 版 2: import UVSeamTool2; UVSeamTool2.tool()
```
