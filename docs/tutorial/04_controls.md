# 4. 操作の入り口 (手順 12〜14)

[目次](README.md) ・ 前: [3. パスと編集](03_path_and_edit.md) ・ 次: [5. 実際のシーンに耐える](05_robust.md)

ボタン・キー・ツール設定のウィンドウ・コマンドのフラグの 4 つの入り口を、**1 つの操作の表** から作る。
入り口ごとに処理を書くと、操作を足すたびに 4 か所を直すことになる (旧版はそうだった)。

## 手順 12: 操作の表とビューのボタン

**ゴール**: ビューの下の中央に、モード・自動・カット N・縫合 N・クリアのボタン。

**方法**

- `core/actions.ACTIONS`: `Action(id, group, label(state), enabled(state), setting= か method=, key=, modes=, value=, button=)`。
  - `setting=` は設定の切り替え (`value=` があればその値にする)、`method=` はコンテキストのメソッドを呼ぶ
  - `label` / `enabled` は今の状態 (`ActionState`: 設定・ためた区間の数・選んだエッジの数…) から決める
  - `modes=` でボタンを出すモード、`button=False` でキーだけ
- `runAction(id)` が表を引いて実行する。ボタン・キー・ウィンドウ・`-runAction` フラグはすべてここを通る
- ボタンの配置 `core/panel.panel_layout` は純粋関数。狭いビューでは 2 段の格子に (段ごとに中央にすると不揃いに見える)
- **ボタンは押せる部品**: 画面の矩形を、ニアクリップのすぐ奥の平面に戻した 3D の四角を `kSelectable` で描く
  (`MUIDrawManager.beginDrawable(kSelectable, glFirstHandle() + 表の番号)`)。押すとマニピュレータの `doPress` に
  `glActiveName()` で届く。2D の描画はハンドルにならない
- **ハンドルの番号は表の番号** (見えるボタンが変わっても、押したボタンの見分けは同じ)
- 実行は離したとき (押したまま外へ動かせばやめられる)。押している間は `doMove` が来ないので、`doDrag` / `doRelease`
  でマウスの下のボタンを調べ直す

**実装**: [core/actions.py](../../core/actions.py)・[core/panel.py](../../core/panel.py)・[tool/drawing.py](../../tool/drawing.py) `ScreenPlane` / `render_panel` / 記録 [10_actions_and_buttons.md](../10_actions_and_buttons.md)

## 手順 13: キー

**ゴール**: Tab / E / V / X / L / C / S / Shift+Esc を、ツールを使っている間、ビューの上でだけ受け取る。

**方法**

- Qt のアプリケーションに**イベントフィルター**を付ける (ツールを有効にしたとき付け、抜けたら外す)
- **ShortcutOverride を accept** すると、Maya のホットキーより先に受け取れる (このあと KeyPress が届く)
- 表に無い修飾キー (Alt など) は Maya に渡す。オートリピートは実行しない
- 受け取ってよいか: マウスが 3D ビューの上 (`cmds.getPanel(underPointer=True)` が modelPanel) で、文字の入力欄に
  フォーカスが無いとき
- キーの重なりを確かめる (E は Maya では回転ツール。受け取らずに渡すとツールを抜けてしまう)
- 同じフィルターで、あとから Qt のダブルクリック・ホイールも受け取る (手順 19・21)

**確かめ方**: mayapy でも Qt のアプリケーションはあるので、`QKeyEvent` を作ってフィルターに直接渡す。

**実装**: [tool/keys.py](../../tool/keys.py) / 記録 [11_keys.md](../11_keys.md)

## 手順 14: ツール設定のウィンドウ

**ゴール**: ツールのアイコンをダブルクリックで、設定の欄・操作のボタン・色の部品が出る。ボタン・キーで変えた値も合わせる。

**方法**

- `stringClassName()` が返す名前 X に対して、Maya は `XProperties()` (部品を作る) と `XValues(ツール名)`
  (値を入れる) の MEL を呼ぶ。**呼ばれる前に定義しておく** (モジュールの import 時に `mel.eval`)
- MEL を **設定の定義表と操作の表から組み立てる** (`core/tool_ui_text`。文字列を作るだけなので pytest できる)
  - BOOL -> `checkBoxGrp`、CHOICE -> `radioButtonGrp`、FLOAT -> `floatSliderGrp`、COLOR -> `colorSliderGrp`
  - どれも `...Grp` にして見出しの列の幅をそろえる。説明は `-annotation` (ツールチップ)
- `Values` の先頭で古いレイアウトを消して `Properties` を呼び直す (最初の 1 回しか呼ばれないらしい)。
  `setParent (toolPropertyWindow -q -location + "|X")` してから部品を名前で操作する
- ボタン・キーで設定を変えたら `XRefreshUI` を呼んで、開いているウィンドウの値を合わせる
- 色の値は MEL の `python("...color_value('key')")` で受け取る (問い合わせは数を 1 つしか返せない)
- 固定の幅だと文字が見切れる: ボタンの幅は文字の幅から決める、説明の欄は `-adjustableColumn`

**実装**: [core/tool_ui_text.py](../../core/tool_ui_text.py)・[tool/tool_ui.py](../../tool/tool_ui.py) / 記録 [12_tool_settings_window.md](../12_tool_settings_window.md)
