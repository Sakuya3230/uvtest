# 段階 7b: ツール設定のウィンドウ

## 目的

ツールのアイコンのダブルクリック (か `UVSeamTool.show_tool_settings()`) で開くツール設定のウィンドウで、
色を変え、保存したガイドの一覧・削除をできるようにする。

| 欄 | 中身 |
|---|---|
| 色 | 設定の表の色ごとの色のスライダー (変えるとすぐ保存し、ビューも変わる)・「色を既定に戻す」 |
| 保存したガイド | ガイドを保存しているメッシュの数・「一覧をスクリプトエディタに出す」・「選んでいるメッシュのガイドを削除」・「シーンのガイドをすべて削除...」(確認する) |
| Reset Tool (ウィンドウの下) | すべての設定を既定に戻す |

## 仕組み

```
ツールを有効にする -> Context.toolOnSetup -> tool_settings_window.define()    MEL の入り口を定義する
ウィンドウを開く   -> Maya が stringClassName ("uvSeamTool") で MEL を呼ぶ
  uvSeamToolProperties()             -> python(... properties())      部品を作る (欄は設定の表の category から)
  uvSeamToolValues("uvSeamToolContext") -> python(... values(名前))   作り直してコマンドを付け、値を入れる
部品を変える -> _command("color_changed", キー) -> settings.current().setValue
設定が変わる (ウィンドウ・api・リセット) -> Context._on_setting_changed -> tool_settings_window.refresh + 描き直し
```

- **入り口だけ MEL**: Maya が名前で呼ぶのは MEL の global proc (`<stringClassName>Properties` / `Values`) だけ。
  中身は `python()` の 1 行で、このモジュールを呼ぶ (ViewPanelLesson の段階 7c と同じ)
- **欄は表から**: 設定の表の `category` ごとに枠を作り、項目を並べる。項目を表に足せば、ウィンドウにも出る
  (今は色だけ。ほかの種類を足したら部品の作り方を足す)
- **フラグを通さない**: 値は `settings.current().setValue` で直接書き、`refresh` で設定から直接読む
- **リロードしても新しいコードが動く**: 部品に渡すのは `_command(名前, ...)`。呼ばれるたびに `sys.modules` から
  今のモジュールを引いて、その名前の関数を呼ぶ

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [tool/tool_settings_window.py](../tool/tool_settings_window.py) | `define` (MEL の入り口)・`open_window`・`refresh`・`properties` / `values` (Maya が呼ぶ)・部品のコマンド |
| [tool/context.py](../tool/context.py) | `stringClassName` (`constants.TOOL_CLASS`)・有効にするたびに `define`・設定が変わったらウィンドウも入れ直す |
| [tool/guide_cleanup.py](../tool/guide_cleanup.py) | 「すべて削除」の確認を api から移した (`delete_all_guides(confirm)`) |
| [constants.py](../constants.py) | `TOOL_CLASS = "uvSeamTool"` |
| [api.py](../api.py) | `show_tool_settings()` |

## 落とし穴

- `colorSliderGrp` などを `-edit` で変えても `changeCommand` は呼ばれない (値を入れ直しても設定に書き戻さない)
- 部品は作ったときに返る **フルパス** で操作する (`_CONTROLS`)。ウィンドウは開くたびに作り直す
- `columnLayout(adjustableColumn=True)` の中のボタンは、幅を指定しても横幅いっぱいに広がる。ボタンは
  `adjustableColumn=False` の列 (`_rows_column`。`rowSpacing` で間隔) に入れ、幅を固定する。ボタンは左の列にラベル、
  右の列にボタンの行 (`_labeled_button`。左の列の幅は色のスライダーのラベルと同じ) にして、色のスライダーと揃える
- standalone (mayapy) には `OptionsTemplate` もツール設定のウィンドウも無い。入り口から Python まで届くことだけを
  確かめた (ウィンドウの中身は GUI で)

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()
UVSeamTool.show_tool_settings()     # ツールのアイコンのダブルクリックでも
# 色を変える -> ビューがすぐ変わる / 「色を既定に戻す」・Reset Tool
# UVSeamTool.settings().setValue("guideColor", (1, 0, 0)) -> ウィンドウの色も変わる
# 保存したガイド: 一覧・選んだメッシュの削除・すべて削除 (確認) -> Ctrl+Z で戻る
```
