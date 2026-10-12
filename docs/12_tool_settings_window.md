# 段階 12: ツール設定のウィンドウ

[目次](README.md) ・ 前: [段階 11](11_keys.md) ・ 次: [段階 13](13_external_changes.md)

## 目的

- ツールのアイコンをダブルクリックすると開く「ツール設定」の欄を作る
- 欄の MEL を **設定の定義表と操作の表から組み立てる** (設定・操作を足せば、欄にもそろって出る)
- ボタン・キーで設定を変えたら、開いている欄の値も合わせる

- 色 (マウスの下の面・拾った頂点 / エッジ・スタート・パス・未実行の区間・カット・縫合) を変えられるようにする

```
▼ パス
    拾うもの        (●) 頂点   ( ) エッジ
▼ カット / 縫合
    自動            [x] 確定と同時に実行する
    自動のときの操作 (●) カット ( ) 縫合
▶ 色 (たたんである)
    マウスの下の面   [■] ━━━●━━━
    ...
    縫合             [■] ━━━●━━━
                    [色を既定に戻す]
▼ 操作
                    [まとめてカット] [まとめて縫合]
                    [クリア]
▶ キーとマウス (たたんである)
                    [設定を既定に戻す]
```

見出しの列 (140px) をすべての部品で揃え、説明の行はやめてツールチップにした
(最初の版は説明の行が部品のあいだに挟まり、ごちゃごちゃして見えた)。

## 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/tool_ui_text.py:162](../core/tool_ui_text.py#L162) `tool_ui_mel` | MEL のプロシージャ (Properties / Values / SetValues / SetColor / RefreshUI) を表から組み立てる |
| [core/tool_ui_text.py:69](../core/tool_ui_text.py#L69) `_setting_control` / [:97](../core/tool_ui_text.py#L97) `_setting_command` / [:120](../core/tool_ui_text.py#L120) `_setting_value` | 設定の種類ごとの部品を作る / 変えたときのコマンドを付ける / 今の値を入れる |
| [core/tool_ui_text.py:39](../core/tool_ui_text.py#L39) `LABEL_WIDTH` / [:134](../core/tool_ui_text.py#L134) `_button_row` / [:151](../core/tool_ui_text.py#L151) `_action_groups` | 見出しの列の幅を揃える / 見出しの列の右に同じ幅のボタンを並べる / 操作のグループごとに行を分ける |
| [core/tool_ui_text.py:60](../core/tool_ui_text.py#L60) `sections` | 設定を欄 (`Setting.section`) ごとに分ける |
| [core/settings.py:28](../core/settings.py#L28) `COLOR` / [:72](../core/settings.py#L72) | 色の設定の種類と、7 つの色の定義 (欄「色」。フラグは持たない) |
| [core/settings.py:50](../core/settings.py#L50) `section` / [:51](../core/settings.py#L51) `check_label` | 欄の名前 / チェックボックスの横の文字 |
| [core/settings.py:151](../core/settings.py#L151) `keys_in_section` / [:209](../core/settings.py#L209) `reset(keys)` | 欄の設定のキー / 一部だけ既定に戻す (色を既定に戻す) |
| [core/draw_list.py:79](../core/draw_list.py#L79) `COLOR_ROLES` / [:90](../core/draw_list.py#L90) `theme_colors` | 色の設定 -> 描画の役割 ({役割: 色}) |
| [tool/drawing.py:128](../tool/drawing.py#L128) `render(colors=)` | THEME の色の代わりに、設定の色で描く |
| [tool/manipulator.py:88](../tool/manipulator.py#L88) `setColors` | マニピュレータが設定の色を持つ |
| [tool/context.py:84](../tool/context.py#L84) `SET_COLOR_FLAG` / [:85](../tool/context.py#L85) `RESET_COLORS_FLAG` / [:363](../tool/context.py#L363) | `-setColor "キー r g b"` / `-resetColors true` |
| [tool/context.py:296](../tool/context.py#L296) `_on_setting_changed` | 色が変わったらマニピュレータへ渡し、開いている欄の値を合わせる (`tool_ui.refresh()`) |
| [core/actions.py:72](../core/actions.py#L72) `title` | 操作に、状態によらない名前を足した (欄のボタン「まとめてカット」など) |
| [tool/tool_ui.py:23](../tool/tool_ui.py#L23) `define` / [:28](../tool/tool_ui.py#L28) `color_value` / [:38](../tool/tool_ui.py#L38) `refresh` | MEL を Maya に定義する (import したとき) / 色の値を MEL へ返す / 開いている欄の値を合わせる |
| [tool/context.py:110](../tool/context.py#L110) `stringClassName` | `"uvPathCut"` (Maya はこの名前で MEL を呼ぶ) |
| [tool/context.py:83](../tool/context.py#L83) `RUN_ACTION_FLAG` / [:384](../tool/context.py#L384) | `-runAction <ID>`: 欄のボタンが操作の表の操作を呼ぶ |
| [tests/UVPathCut/test_tool_ui_text.py](../../tests/UVPathCut/test_tool_ui_text.py) | 組み立てた MEL の中身 (揃った見出しの列・ツールチップ・色の部品) |
| [tests/UVPathCut/test_settings.py](../../tests/UVPathCut/test_settings.py) / [test_draw_list.py](../../tests/UVPathCut/test_draw_list.py) | 色の normalize・一部のリセット / `theme_colors` |
| [tests/UVPathCut/mayapy/test_tool_ui.py](../../tests/UVPathCut/mayapy/test_tool_ui.py) / [test_prefs.py](../../tests/UVPathCut/mayapy/test_prefs.py) | MEL を Maya が読めるか・色が MEL の float[] で届くか / 色の保存と読み直し |

## 仕組み

### Maya がツール設定の欄を作る流れ

```
ツールのアイコンをダブルクリック (かツールを有効にする)
  -> stringClassName() = "uvPathCut"
  -> MEL の uvPathCutProperties()           部品を作る (値は入れない)
  -> MEL の uvPathCutValues("uvPathCutContext")
       古いレイアウトを消して Properties を呼び直す (最初の 1 回しか Properties が呼ばれないらしいため)
       setParent してから、部品を名前だけで操作する
       部品に「変えたときのコマンド」を付ける   uvPathCutCtx -edit -<キー> <値> <ツールの名前>
       uvPathCutSetValues                     今の値を入れる (uvPathCutCtx -q -<キー>)
```

プロシージャは呼ばれる前に定義しておく必要がある。`tool/tool_ui.py` を import したとき
(= コンテキストのモジュールを import したとき = プラグインを読み込んだとき) に `mel.eval` で定義し、
リロードで import し直すと新しい表で定義し直す。

### 表から組み立てる

| 設定の種類 | 部品 | 変えたとき | 値を入れる |
|---|---|---|---|
| BOOL | `checkBoxGrp` (見出し + チェック) | `-changeCommand1` で `-<キー> #1` | `-value1` に問い合わせの結果 |
| CHOICE | `radioButtonGrp` (選択肢の表示名) | `-onCommandN` で `-<キー> <選択肢>` | `-select` に番号 + 1 |
| FLOAT | `floatSliderGrp` (範囲) | `-changeCommand` で `-<キー> #1` | `-value` |
| COLOR | `colorSliderGrp` (四角をクリックで色の選択) | `-changeCommand` で `uvPathCutSetColor <キー>` | `-rgb` に `python("...color_value('キー')")` |

どの部品も `...Grp` にして `-columnWidth 1 140` で見出しの列を揃える (`checkBox` だけだと左端がずれる)。
説明 (`Setting.description`) は `-annotation` (ツールチップ) にする。

### 色

色は 7 つの設定 (`faceColor` など。欄「色」) で、描画の役割に `COLOR_ROLES` で当てる
(例: `pendingColor` -> 未実行の区間の線と端の点)。

```
欄の色を変える
  -> uvPathCutSetColor cutColor <ツール>       (MEL。colorSliderGrp -q -rgb で r g b を読む)
  -> uvPathCutCtx -e -setColor "cutColor 1 0.3 0.3" <ツール>
  -> settings.set("cutColor", "1 0.3 0.3")      (normalize が (1.0, 0.3, 0.3) にして保存)
  -> _on_setting_changed -> manip.setColors(theme_colors(values))
  -> drawUI の render(..., colors) が THEME の色の代わりに使う
```

色の値は、コンテキストのコマンドの問い合わせでは返せない (`setResult` は数を 1 つだけ)。
そこで欄の `SetValues` は MEL の `python()` で `tool_ui.color_value(キー)` を呼び、Python のリストを
MEL の `float[]` として受け取る (設定は変えるたびに optionVar に保存されるので、保存先から読めば今の値)。
「色を既定に戻す」は `-resetColors true` (`reset(keys_in_section("色"))`。ほかの設定は残す)。

メソッドの操作 (まとめてカット・縫合・クリア) は「操作」の欄のボタンにして、`-runAction <ID>` で
`runAction` を呼ぶ。ビューのボタン・キー・欄のボタンが、すべて同じ `runAction` を通る。

### 欄の値を合わせる

ビューのボタンやキーで設定を変えると、設定のリスナー (`_on_setting_changed`) が `tool_ui.refresh()` を呼び、
MEL の `uvPathCutRefreshUI` が開いている欄の値を入れ直す (欄が無い・別のツールなら何もしない)。

## 落とし穴

- `Values` の先頭で `setParent (toolPropertyWindow -q -location + "|uvPathCut")` してから部品を名前だけで操作する。
  しないと「Object not found」(ブラシで確認)
- `Properties` はそのクラス名で最初に使ったときの 1 回しか呼ばれないらしい (プラグインを読み直すと前の版の
  部品が残った)。`Values` の先頭で古いレイアウトを消して、`Properties` を自分で呼び直す
- 問い合わせは文字列を返せないので、選択肢は番号で返る。`radioButtonGrp -select` は 1 から
- `radioButtonGrp` の `-labelArrayN` は 2〜4 個まで (それより多い選択肢はエラーにする)
- MEL の文字列に入れる文字は、`"` と `\` をエスケープする (`mel_string`)
- 問い合わせは数を 1 つしか返せないので、色 (3 つの数) は `-q` で受け取れない。`python()` で Python から受け取る
- 色はフラグを持たない (`short_flag` が None)。色ごとにフラグを足すとフラグが増えすぎるので、`-setColor "キー r g b"` 1 つにした
- `colorSliderGrp` は列の幅を決めないと色の四角が横に伸び、明るさのスライダーが見えなくなる (`-columnWidth3 140 50 160`)
- ボタンの幅を固定すると長い文字が見切れる (「Maya の設定を読み込む」。段階 17)。`_button_width` で文字に合わせて広げる (同じ行は同じ幅)
- 文字の色 (ボタンの文字など) は色の設定の対象にしない (読みやすさのため白 / 黒で固定)

## 試し方

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polySphere()
import UVPathCut; UVPathCut.tool()
# ツールのアイコン (ツールボックスの今のツール) をダブルクリック -> ツール設定に「パス」「カット / 縫合」「操作」
# 1. 欄で拾うもの・自動・自動の操作を変えると、ビューのボタンの文字も変わる
# 2. ビューのボタン・Tab で変えると、欄の値も変わる
# 3. 「まとめてカット」「まとめて縫合」「クリア」がビューのボタンと同じに動く
# 4. 「色」の欄を開き、四角をクリックして色を変える -> ビューの描画の色がすぐ変わる
#    (Maya を再起動しても残る。「色を既定に戻す」で色だけ戻る)
# 5. 「設定を既定に戻す」 (色も戻る)
# スクリプトからも: cmds.uvPathCutCtx("uvPathCutContext", e=True, setColor="cutColor 0 0.6 1")
```
