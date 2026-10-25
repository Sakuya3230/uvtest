# 段階 20: コンテキストの基底を MPxContext に・エッジの選択モードを保つ

## 目的

1. 選択はサブツールが全部自前で行う (16b) ので、コンテキストの基底を `MPxSelectionContext` から `MPxContext` に替える
2. ツールを使っている間に、選択のモード・種類 (F8〜F12 のホットキー・マーキングメニュー・ステータスラインのボタンなど) を
   替えられて誤操作になるのを防ぐ。替えられたら、すぐエッジの選択モードに戻す

## 基底を替えても、モードの切り替えは止まらない

ホットキー・マーキングメニュー・ステータスラインは Maya 側の仕組みで、どのコンテキストでも効く。なので 2 は別に作る。
基底を替えたのは「Maya の選択は使わない」をコードの上でもはっきりさせるため (受け取らなかったクリックは何もしない)。
使っているメソッド (`doPtrMoved`・`drawFeedback`・`completeAction` / `abortAction` / `deleteAction`・
`toolOnSetup` / `toolOffCleanup`・`stringClassName`・`setTitleString`) は、どれも MPxContext にある (2022・2027 で確認)。

## 仕組み (モードを保つ)

```
toolOnSetup 2. SelectionWatcher(_on_select_mode_changed, SELECT_MODE)   SelectModeChanged・SelectTypeChanged を見張る
替えられた -> 手すきのときに 1 回 _on_select_mode_changed
                自分で替えている途中 (_own_mode) なら何もしない
                is_edge_mode (今もエッジだけを選べる状態か) なら何もしない (選択の優先度だけ変わったなど)
                そうでなければ _enter_edge_mode -> ログ「ツールを使っている間はエッジの選択モードです」
_enter_edge_mode: _own_mode を立てて enter_edge_mode、次の手すきのときに下ろす (自分で替えた知らせでは戻さない)
toolOffCleanup 2. 見張りを外す
```

`is_edge_mode` は、コンポーネントの選択モードならエッジだけが選べるか、オブジェクトの選択モードなら対象のメッシュが
すべてハイライトされていてエッジだけが選べるか (`selectType -objectComponent`) を調べる。自分の戻す操作の知らせで
もう一度戻す、という繰り返しを、この判定と `_own_mode` の 2 つで止める。

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [tool/context.py](../tool/context.py) | 基底を `omui.MPxContext` に (`doPress` / `doDrag` / `doRelease` は基底を呼ばない)・`_on_select_mode_changed`・`_enter_edge_mode` |
| [utils/selection_watcher.py](../utils/selection_watcher.py) | 見張るイベントを渡せるように (`SELECTION` / `SELECT_MODE`) |
| [utils/selection.py](../utils/selection.py) | `is_edge_mode(meshes)` |

## 落とし穴

- standalone の mayapy では `selectMode` / `selectType` の問い合わせが None を返す (GUI でしか確かめられない)
- 戻すのは「手すきのとき」なので、替えた直後に一瞬だけ別のモードが見える
- ツールを抜けるとき (段階 19) にエッジの選択モードにするのは、見張りを外す前。届く知らせは見張りを外したあとなので戻さない

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()
# F9 (頂点)・F11 (面)・F8・右クリックのマーキングメニューの「頂点」 -> すぐエッジの選択モードに戻り、ログが出る
# ツールを抜けたあとは、F9 などで普通に切り替わる
```
