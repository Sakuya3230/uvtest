# 段階 10: 操作の表とボタン、リセット

[目次](README.md) ・ 前: [段階 9](09_cut_and_sew.md)

## 目的

- 操作 (切り替え・まとめて実行・リセット) を **操作の表** 1 か所で決める。ボタン (この段階)・
  キー (段階 11)・ツール設定のウィンドウ (段階 12) は、すべてこの表から作る
- ビューの下の中央に、押せるボタンを並べる
- **リセット** (区間・スタート・エッジの選択をすべて外す。1 回の Undo で戻せる)

```
[エッジ] [自動 ON] [自動:カット]   [カット 2] [縫合 2]   [クリア]
```

## 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/actions.py:72](../core/actions.py#L72) `ACTIONS` | 操作の表 (ID・組・文字・押せるか・設定の切り替え / メソッド・説明) |
| [core/actions.py:44](../core/actions.py#L44) `Action` / [:34](../core/actions.py#L34) `ActionState` | 操作 1 つ / 文字と押せるかを決める今の状態 |
| [core/actions.py:100](../core/actions.py#L100) `next_setting_value` | 設定の切り替えの次の値 (真偽値は反対、選択肢は次) |
| [core/panel.py:36](../core/panel.py#L36) `panel_layout` / [:54](../core/panel.py#L54) `button_at` / [:62](../core/panel.py#L62) `button_state` | ボタンの配置 (下の中央に 1 段、組の間は広く) / 位置からボタン / 状態の名前 |
| [scene/edit.py:141](../scene/edit.py#L141) `ResetChange` | 区間とスタートを外す (undo で戻す) |
| [scene/edit.py:271](../scene/edit.py#L271) `clear_session` | リセット (ResetChange + 選択を空に。1 回の Undo) |
| [tool/drawing.py:162](../tool/drawing.py#L162) `ScreenPlane` | 画面のピクセルを 3D に戻す (押せる部品にするため) |
| [tool/drawing.py:187](../tool/drawing.py#L187) `render_panel` | ボタンの四角 (kSelectable) と文字 (text2d) |
| [tool/manipulator.py:134](../tool/manipulator.py#L134) | ボタンの上ではメッシュを拾わず、ホバーを覚える |
| [tool/manipulator.py:159](../tool/manipulator.py#L159) `doPress` / [:169](../tool/manipulator.py#L169) `doRelease` | 押したボタンを覚え、離したときに同じボタンの上なら実行 |
| [tool/manipulator.py:209](../tool/manipulator.py#L209) `panelButtons` | 表と今の状態から、ボタンの (ID, 文字, 押せるか, 状態) |
| [tool/context.py:224](../tool/context.py#L224) `runAction` | 表を引いて、設定を切り替えるかメソッドを呼ぶ (押せない状態なら何もしない) |
| [tool/context.py:216](../tool/context.py#L216) `actionState` | 今の状態 (設定・未実行の数・区間の数・スタートの有無) |
| [tool/context.py:198](../tool/context.py#L198) `clearAll` / [:70](../tool/context.py#L70) `CLEAR_FLAG` | リセット / `-clear` |
| [tests/UVPathCut/test_actions.py](../../tests/UVPathCut/test_actions.py) | 表・文字・押せるか・配置 (pytest 6 件) |
| [tests/UVPathCut/mayapy/test_edit.py](../../tests/UVPathCut/mayapy/test_edit.py) | リセットと Undo の整合 (mayapy 1 件) |

## 仕組み

### 操作の表

```python
Action("applyCut", GROUP_APPLY, lambda state: "カット {}".format(state.pending),
       enabled=lambda state: state.pending > 0, method="applyPending", args=("cut",),
       description="ためた区間をまとめてカットする")
```

| 項目 | 意味 |
|---|---|
| `id` | 操作の名前 (ボタン・キー・ツール設定がこれで呼ぶ) |
| `group` | 組 (切り替え / まとめて実行 / リセット)。ボタンの並びで組の間を空ける |
| `label(state)` | ボタンの文字 (状態で変わる: 「カット 2」「自動 OFF」) |
| `enabled(state)` | 押せるか (ためた区間が無ければ「カット」は押せない) |
| `setting` / `method` + `args` | 何をするか: 設定を切り替える / コンテキストのメソッドを呼ぶ |

旧版では、操作を足すたびに 5 か所 (定数・ボタンの並び・キーの表・`runAction` の if の連鎖・MEL) を
直していた。今は表に 1 行足せば、ボタン・キー・ツール設定にそろって出る。

### ボタンを押す流れ

```
マニピュレータ.drawUI
  panelButtons(): 表 x 今の状態 (コンテキストの actionState) -> (ID, 文字, 押せるか, 状態)
  render_panel: 四角を kSelectable (ハンドル = glFirstHandle() + 表の番号) で 3D に描き、文字を重ねる
押す   -> マニピュレータ.doPress   glActiveName() - glFirstHandle() で表の番号 -> 押した ID を覚える
離す   -> マニピュレータ.doRelease  まだ同じボタンの上なら action_handler(ID)
       -> コンテキスト.runAction(ID)
            押せない状態なら何もしない
            setting なら Settings.set(次の値)   (設定のリスナーが、拾うものの切り替えなどを届ける)
            method なら getattr(self, method)(*args)   (applyPending("cut") / clearAll())
```

- 2D の部品 (rect2d・text2d) は押せない (ウェイトスライダーで確認)。四角は `ScreenPlane` で画面の矩形の
  角を 3D の点に戻して三角形で描く。平面はカメラのニアクリップの 1.5 倍の距離 (手前のメッシュに隠れない)
- ボタンの上の押下はマニピュレータに届き、メッシュの上の押下はコンテキストに届く (段階 7)。
  ボタンの上ではメッシュを拾わないので、奥の頂点 / エッジを確定してしまうこともない
- 離したときに実行するので、押したまま外へ動かせばやめられる

### リセット

```
clear_session(session)
  -> [ResetChange (区間とスタートを外す。undo で戻す), SelectionChange (選択を空に。undo で戻す)]
  -> run_changes (1 回の Undo。「UV パスのクリア (3 区間)」)
```

区間のスタックは Undo できるコマンドだけが積み下ろしするので、リセットも Undo に載せる。
載せずに空にすると、そのあとの Ctrl+Z (確定の undo) が空のスタックから取り出そうとして壊れる。
テスト `case_clear_session_and_undo` は、クリア → Undo → さらに Undo (確定が 1 区間ずつ戻る) を確かめている。
UV のカット / 縫合は戻さない (ツールの記録だけを外す)。まだ実行していなかった区間は確認せずに捨て、数をログに出す。

## 落とし穴

- 2D の部品は kSelectable にしても押せない。押せる部品は 3D で描く
- ボタンの平面を遠くに置くと、手前のメッシュに隠れる。ニアクリップのすぐ奥に置く
- 状態の変化 (ためた区間の数など) でボタンの文字が変わるので、描くたびに表と状態から作る (覚えておかない)
- **押している間 (ドラッグ中) は `doMove` が呼ばれない**。押したまま外で離すとホバーの色が残っていた
  (GUI で発見)。`doDrag` と `doRelease` でマウスの下のボタンを調べ直し、押した色は「押したボタンの上に
  いるときだけ」にした (`button_state`。外へ出たら普通の色 = 離せばやめられる、と分かる)
- **対象のメッシュを消しても、描画が残ってクリックでエラーになった** (GUI で発見)。マニピュレータは
  最後に拾ったものを覚えたままで、マウスを動かすまで古いままだった。`MeshModel.isValid()`
  (`MObjectHandle.isValid`。消して Undo のキューにだけ残っているときも False) を、描く・拾う・
  クリックを受け取る・まとめて実行の前に確かめる。Undo でメッシュが戻れば同じノードなので、続きから使える。
  変形・トポロジーの変更まで含めた検知は段階 13
- **ビューを横に狭めると、ボタンが見切れた** (段階 11 の確認で指摘)。1 段でビューの幅に収まらなければ、
  組の切れ目で 2 段に分ける (`core/panel.py` の `panel_rows`。両方の段が収まり、長いほうの段がいちばん
  短い切れ目。組の切れ目で収まらなければ組の途中で分ける)。下の段は今までの高さ、上の段はその上。
  2 段のときは **格子** に並べる (上下の段で列の位置を揃え、間隔はすべて同じ)。はじめは段ごとに中央に
  揃えていたが、下の段だけ組の間隔が入って幅が違い、上下でボタンがずれて不揃いに見えた。
  あわせてボタンを幅 80・高さ 24 (文字のまわりの余白)、間隔 6 / 段の間 6 / 組の間 14 に広げた。
  今の 6 つのボタンでは、ビューの幅 534 未満で「切り替え 3 つ」/「まとめて実行・クリア 3 つ」の 2 段になる。
  2 段でも収まらない幅 (264 未満) では左端を余白に寄せる (2 段までの想定)
- **未実行の区間の水色が、エッジの選択モードのワイヤーフレーム (水色) と見分けにくかった** (GUI で指摘)。
  マゼンタ (`THEME` の `ROLE_CONFIRMED`) に変えた。色は使っていない系統 (黄・橙・緑・赤・水色・
  Maya の選択の橙と重ならない)。暗い縁取り (下に敷く太い線) も試したが、エッジ 1 本ずつの線分なので
  頂点ごとに継ぎ目が見えて見苦しく、やめた

## 試し方

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polySphere()
import UVPathCut; UVPathCut.tool()
# 1. ビューの下の中央にボタンが並ぶ。「エッジ」を押すと「頂点」に (拾うものも変わる)
# 2. 「自動 ON」を押して OFF にし、確定すると「カット 1」「縫合 1」が押せるようになる。押すとまとめて実行
# 3. 「クリア」で区間・スタート・選択がすべて外れる。Ctrl+Z で戻る
# 4. ボタンの上をクリックしても、奥のメッシュで確定されない
cmds.uvPathCutCtx("uvPathCutContext", edit=True, clear=True)   # フラグでもクリア
```
