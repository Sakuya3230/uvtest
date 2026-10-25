# 段階 4: ビューの上のパネル (作成 / 編集・カット・縫合)

## 目的

カット / 縫合を api の関数ではなく、ツールの中のボタンで行う。あわせて、モード (作成 / 編集) を切り替える入り口を作る。
編集のサブツールはまだ空 (ガイドを描くだけ)。切り替えの仕組みを先に確かめる。

| ボタン | 動き |
|---|---|
| 作成 / 編集 | モードを切り替える (今のモードのボタンが押された見た目) |
| カット / 縫合 | 作成のモード: 作成中のガイド / 編集のモード: 確定したガイドすべて (選べるようになるまで) |

パネルはアクティブなビューの下の中央に置き、ビューに付いて回る。

## 流れ

```
toolOnSetup
  -> TargetMesh(mesh)                         対象のメッシュのグラフ・描画用の位置 (作成と編集で共有)
  -> {作成: CreateTool, 編集: EditTool}         サブツールを 2 つ作り、作成にする
  -> panel_host.open_panel(_on_action)        (tool) ViewPanel + PanelFollower
ボタン
  -> ViewPanel.actionTriggered(ID)            (ui) 何をするかは知らない
  -> Context._on_action(ID)
       モードの ID -> _set_mode: 今のサブツールを入れ替える (deactivate -> activate)
       cut / sew   -> 今のサブツール.applyOperation(ID) -> uv_apply.apply_guides
0.25 秒ごと
  -> PanelFollower.place                      (ui) ビューの下の中央へ。ビューが見えなければ隠す
```

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [ui/view_panel.py](../ui/view_panel.py) | `ViewPanel`: ボタンを横に並べた枠なしの Tool ウィンドウ。押されたら `actionTriggered(ID)`。`remove_panels()` |
| [ui/panel_follower.py](../ui/panel_follower.py) | `PanelFollower`: 0.25 秒ごとにビューの下の中央へ置き直す。ビューは関数で受け取る (Maya を知らない) |
| [compat/qt.py](../compat/qt.py) | (段階 3 の右クリックで作った) |
| [utils/view.py](../utils/view.py) | `active_view_pointer()` |
| [tool/actions.py](../tool/actions.py) | モードの名前・パネルのボタンの表 `PANEL_ACTIONS`・モードごとのヘルプ |
| [tool/panel_host.py](../tool/panel_host.py) | `open_panel` / `close_panel`: Maya のビューを Qt のウィジェットにして ui に渡す |
| [tool/target_mesh.py](../tool/target_mesh.py) | `TargetMesh`: メッシュ・鍵・グラフ・描画用の位置 (前は CreateTool が持っていた) |
| [tool/guide_drawing.py](../tool/guide_drawing.py) | `draw_guides` と色 (作成と編集で共通) |
| [tool/uv_apply.py](../tool/uv_apply.py) | `apply_guides(mesh, graph, guides, CUT / SEW)` |
| [tool/edit_tool.py](../tool/edit_tool.py) | `EditTool`: 今はガイドを描くだけ |
| [tool/sub_tool.py](../tool/sub_tool.py) | `applyOperation(operation)` を足した |
| [tool/create_tool.py](../tool/create_tool.py) | `TargetMesh` を使う形に。`applyOperation` は作成中のガイド |
| [tool/context.py](../tool/context.py) | サブツールの表とモードの切り替え・パネル |

## 仕組み

- **狭いビューでは折り返す** (段階 18 で足した): `PanelFollower.place` が毎回 `ViewPanel.fitWidth(ビューの幅 - 余白)` を呼び、
  段の分け方 (`split_rows`) が変わったときだけ並べ直して大きさを合わせる
- **小さいボタンと区切り線** (段階 21 のあとで変えた): 丸は 32px・ボタンの幅 52px・ラベルは 10px の字。`PANEL_ACTIONS` の
  `SEPARATOR` の所に縦線 (`ui/panel_separator.py`)。部品の位置はレイアウトを使わず自分で決める (`_arrange`)。段の始め・終わりに
  来た区切り線は出さない

- **ui は Maya を知らない**: `ViewPanel` はボタンの表を受け取って並べ、押されたらシグナルを出すだけ。`PanelFollower` は
  ビューを `view_provider()` で受け取る。Maya のビューを Qt のウィジェットにするのは `tool/panel_host.py`
- **モードの切り替え = サブツールの入れ替え**: コンテキストはモード -> サブツールの表を持ち、今のサブツールを替えるだけ。
  マウス・キー・描画・カット / 縫合は、どれも今のサブツールに渡る。モードを足すときはサブツールと表の 1 行を足す
- **カット / 縫合の対象はサブツールが決める**: コンテキストは `applyOperation(ID)` を呼ぶだけ
- **追従は見回りだけ**: ViewPanelLesson の段階 2 はイベントフィルターと見回りの両方を使うが、ここでは 0.25 秒ごとの
  見回りだけにした (最小限)。ビューの下の中央に置き、ビューが見えない・持ち主が最小化なら隠す。ビューを切り離して
  浮かせたら、持ち主をそのウィンドウに付け替える

## 落とし穴

- **押してもフォーカスを奪わない**: ウィンドウに `WindowDoesNotAcceptFocus`、ボタンに `NoFocus`。フォーカスを取ると、
  押したあとに W / E / R などの Maya のキーが効かなくなる (ViewPanelLesson の最小化のタブと同じ方法)
- 持ち主を付け替えるときは `setParent(新しい持ち主, panel.windowFlags())` (フラグを渡さないと子ウィジェットに戻る)
- `raise_()` は出し直すときだけ (毎回呼ぶと、スクリプトエディタなどほかの浮いたウィンドウの上に割り込む)
- 見回りだけなので、Maya のウィンドウを動かすと最大 0.25 秒遅れて付いてくる (気になればイベントフィルターを足す)
- パネルは `toolOffCleanup` で閉じる。リロードのあとも `remove_panels()` が objectName で残りを消す
- 作成中のガイドがあるまま編集のモードにすると、確定する (ユーザーの指定。ツールを抜けたときも。`CreateTool.deactivate`)

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere()
UVSeamTool.tool()
# ビューの下の中央に [作成][編集][カット][縫合]
# 作成: 点を置く -> [カット] で作成中のガイドを切る / Enter で確定 -> [編集] -> [カット] で確定したガイドすべて
# Maya のウィンドウを動かす・ビューを最大化 (スペース) -> 付いてくる / ツールを抜ける (W) -> パネルが消える
```

mayapy (offscreen。2022 の PySide2 / 2027 の PySide6) で、ボタンのシグナル・切り替えの見た目・ビューの下の中央の位置・
ビューが隠れたら隠すことを確かめた。

## 追加: 丸いボタン

小さくて誤操作しそうなので、丸いボタン (直径 44px・アイコン + 下にラベル) にした。

| 状態 | 見た目 |
|---|---|
| 普通 | 灰 |
| ホバー | 黄 |
| 押している間 | 水色 |
| 選ばれている (作成 / 編集の今のモード) | 水色 (ホバーすると縁だけ黄) |

| ファイル | 中身 |
|---|---|
| [ui/round_button.py](../ui/round_button.py) | `RoundButton` (QAbstractButton)。`paintEvent` で丸・アイコン・ラベルを描く。`hitButton` で丸の上だけを押せる所にする |
| [ui/icons.py](../ui/icons.py) | `draw_icon(painter, 名前, rect, 色)`。作成 (点と線)・編集 (四方の矢印)・カット (はさみ)・縫合 (縫い目) を QPainter で描く。足すときは関数と `_ICONS` の 1 行 |
| [ui/view_panel.py](../ui/view_panel.py) | QPushButton を RoundButton に替えた。アイコンはボタンの ID と同じ名前 |

- アイコンは画像のファイルを使わない (Maya の版ごとの置き場所を気にしない・色を状態に合わせて変えられる)
- 塗りが明るい (黄・水色) ときはアイコンを暗い色にする
- ホバーは `underMouse()` で見て、`enterEvent` / `leaveEvent` で描き直す
- 切り替えのボタンは押すと Qt が checked を反転させるが、そのあとコンテキストが `setChecked` で今のモードに合わせ直す
- offscreen で画像にすると日本語のラベルが □ になる (フォントが無いため。GUI では出る)
