# 段階 22: パネルの表示の設定とマーキングメニュー

## 目的

ボタンが増えてパネルが場所を取るので、パネルを設定で消せるようにし、代わりにラジアルメニューを用意する。

| 操作 | 動き |
|---|---|
| 設定「ビューのパネルを表示」(分類「表示」、既定オン) | オフにするとパネルを消す (ツールを使っている間に変えてもすぐ出し入れする) |
| ビューで Shift+右クリック | ツールのマーキングメニュー (Maya のマーキングメニュー。ツールを使っている間だけ) |

## 決めたこと (ユーザーの選択)

- 表示 / 非表示はパネルごと (ボタンごとではない)
- ラジアルメニューは Maya のマーキングメニュー (`cmds.popupMenu(markingMenu=True)`)。見た目・操作 (ドラッグの向き・
  ジェスチャー) が Maya と同じ
- 出し方は Shift+右クリック (右クリックの確定・Maya のマーキングメニューとぶつからない)

## メニューの中身

ユーザーの提案で、対称・モード・自動を子のマーキングメニューにまとめた (Maya の対称のメニューと同じく、子も向きで選ぶ)。

```
                    対称 >
          モード >          自動 >
                縫合    カット
------------------------
全削除
パネルを表示 (チェック)
------------------------
ツール設定...

対称 >    N 対称 (オン / オフ)   W ワールド   E オブジェクト   SW X 軸   S Y 軸   SE Z 軸
モード >  N 作成   E 編集   S 選択   W ループ
自動 >    N 自動 (オン / オフ)   E 自動カット   S 自動縫合
```

チェックで今の状態を見せる (モード・ループ・対称・空間・軸・自動・自動の操作・パネルを表示)。選ぶとパネルのボタン・キーと
同じ `ToolActions.trigger(ID)` を呼ぶ。空間・軸・自動の操作は「設定を 1 つの値にする」操作 (`actions.SET_SETTINGS` の表)。
Maya の対称がオンの間は Maya の空間・軸が効く (選ぶとログで知らせる)。

## 仕組み

最初は自分のメニューを `viewPanes` に付けた (`cmds.popupMenu(parent="viewPanes", markingMenu=True, button=3,
shiftModifier=True)`) が、**GUI では Maya の標準のメニューが出た**。ビューの右ボタンのメニューは、各ビューに Maya の
`ModelEdMenu.mel` が付けたもの (`<パネル>ObjectPop` = 右クリック、`ConvertPop` = Ctrl、**`CommandPop` = Shift**、
`ToolOptionsPop` = Ctrl+Shift) が先に出すため。そこで、Shift+右クリックの標準のメニュー `CommandPop` の中身を作る関数
(postMenuCommand) を、ツールの間だけ差し替える形にした。

```
ToolActions.install -> MarkingMenu(trigger, states)
  cmds.lsUI(type="popupMenu") の名前が CommandPop で終わるもの (各ビューの Shift+右クリックのメニュー) ごとに
    postMenuCommand を Python の関数 (_build) に差し替える
開くたび  _build: 項目を消して作り直す (表 actions.MARKING_MENU の順と置き場所、表示名とチェックは states())。
          3 つ組の項目は subMenu=True で子のメニューを作り、setParent で中へ入って足して戻る
ToolActions.release -> MarkingMenu.release
  postMenuCommand を Maya と同じ MEL のコマンド contextToolsMM "<メニューのフルパス>" に戻す (MEL の popupMenu -edit で)
```

- `states()` は {ID: (表示名, チェック)} を返す。パネルのボタンの見た目 (`sync`) もこれから作るので、
  パネルとメニューの見た目は同じ所で決まる
- 右クリックのフィルター (`ViewInputFilter`) は Shift 付きの右クリックを受け取らない (Maya に渡し、マーキングメニューを出させる)
- パネルの出し入れは `_show_panel(visible)`。設定が変わったら `_on_setting_changed` から

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [tool/marking_menu.py](../tool/marking_menu.py) | `MarkingMenu` (標準の Shift+右クリックのメニュー CommandPop の postMenuCommand の差し替えと戻し) |
| [tool/actions.py](../tool/actions.py) | `MARKING_MENU` (項目と置き場所)・`SHOW_PANEL` |
| [tool/tool_actions.py](../tool/tool_actions.py) | `states`・`_show_panel`・`sync` (段階 23 で context から分けた) |
| [tool/view_input.py](../tool/view_input.py) | Shift+右クリックは受け取らない |
| [core/settings/definitions.py](../core/settings/definitions.py) | `showPanel` (分類「表示」) |

## 落とし穴

- **postMenuCommand は問い合わせできない** (`RuntimeError: No flags found that can be queried.`)。元の文字列は覚えられないので、
  ModelEdMenu.mel と同じ形で組み立てて戻す (2022・2027 とも `contextToolsMM`)
- **cmds に文字列のコールバックを渡すと Python のコードとして扱われる**。`cmds.popupMenu(..., postMenuCommand='contextToolsMM ...')`
  で戻したら、ツールを抜けてもツールのメニューのままだった (MEL として呼ばれず、項目が作り直されない)。戻すのは
  `mel.eval('popupMenu -edit -postMenuCommand "..." "..."')` で (`_restore`)
- standalone の mayapy にはビューのメニューが無い (差し替えは GUI でしか確かめられない)
- ツールを使い始めたあとにできたビュー (切り離したパネル・レイアウトを替えて初めて表示したビュー・別のウィンドウのビュー) の
  メニューは、ToolActions の 0.5 秒ごとの見回り (`MarkingMenu.hookNewViews`) で差し替える (パネルの見回りとは別の QTimer。
  パネルを消している設定でも動く)。名前の一覧 (`lsUI`) と差し替え済みの名前を比べるだけ。パネルを切り離すとフルパスが変わるので、
  新しいパスとして差し替え直す (戻すときは、今あるパスだけを戻す)
- 差し替えている間の Shift+右クリックは、Maya の Shift+右クリックのメニュー (コンポーネントの操作) の代わりにこのメニューになる

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()
# ビューで Shift+右クリック -> メニュー -> 「編集」へドラッグ / 「パネルを表示」を外す -> パネルが消える
# ツールを抜けたあとの Shift+右クリックは Maya のいつものメニュー
```
