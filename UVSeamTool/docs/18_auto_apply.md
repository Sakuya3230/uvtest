# 段階 18: 自動のカット / 縫合

## 目的

旧版の「自動」(確定と同時にカット / 縫合) を、ガイドの形に合わせて作る。

| 操作 | 自動がオンのとき |
|---|---|
| 作成のモードで点を足す | 足した区間 (最後の点 -> 足した点) のエッジに、すぐカット / 縫合する。対称なら相手の区間にも |
| Ctrl+Z | 点を足したのと、当てたカット / 縫合が一緒に戻る (1 回の Undo) |
| 編集のモード (動かす・挿入・削除) | 当てない |
| パネルの「自動」・A キー | オン / オフ (設定 `autoApply`。ツール設定のウィンドウの「カット / 縫合」にもある) |
| パネルの「自動カット / 自動縫合」・Shift+A | 自動のときの操作をカット <-> 縫合に切り替える (設定 `autoOperation`)。ボタンのアイコンとラベルが今の操作を見せる |

## 決めたこと (ユーザーの選択)

- **点を足すたびに当てる** (旧版と同じ。確定したときにまとめて当てる形にはしない)
- **オン / オフと操作は別のボタン・別のキー** (A / Shift+A)。1 つのキーで回すと、カットのままオフにするのに縫合を通る・押した回数で状態が決まって分かりにくいため
- **編集のモードでは当てない**: ガイドは UV の状態を持たない (段階 13) ので、点を動かしても前の位置の切れ目は戻せない。
  編集で直したら C / S で当てる

## 仕組み

```
CreateTool.press -> auto_apply.add_point(target, 点を足した組)
  自動がオフ -> guide_edit.apply だけ (今までどおり)
  自動がオン -> undo.chunk の中で
                  guide_edit.apply                (ガイドの組を変える。対称なら相手も作り直す。自分の Undo コマンド)
                  _last_segment_edges             作成中のガイド (と相手) の最後の区間のエッジ
                  uv_apply.apply_edges            polyMapCut / polyMapSew
```

自分の Undo コマンド (ガイド) と Maya のコマンド (UV) を `undo.chunk` で 1 つにまとめるので、Ctrl+Z 1 回で両方が戻る。
最初の点 (区間がまだ無い) では何もしない。

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [tool/auto_apply.py](../tool/auto_apply.py) | `add_point(target, new_set)`・`_last_segment_edges` |
| [tool/create_tool.py](../tool/create_tool.py) | 点を足すのを `auto_apply.add_point` に |
| [core/settings/definitions.py](../core/settings/definitions.py) | 分類「カット / 縫合」: `autoApply` (既定オフ)・`autoOperation` |
| [tool/actions.py](../tool/actions.py) / [tool/context.py](../tool/context.py) / [ui/icons.py](../ui/icons.py) | ボタン「自動」(切り替え・稲妻のアイコン)・「自動カット / 自動縫合」(`_sync_panel` がアイコンとラベルを替える)・A / Shift+A・切り替えたらログに出す |
| [ui/view_panel.py](../ui/view_panel.py) / [ui/round_button.py](../ui/round_button.py) | `ViewPanel.setAppearance(ID, アイコン, ラベル)`・`RoundButton.setIconName` |
| [tool/view_input.py](../tool/view_input.py) | ツールのキーに Shift 付き (`"Shift+A"`) を書けるように (`_key_of`。Ctrl・Alt 付きは今までどおり Maya に渡す) |

## 落とし穴

- A / Shift+A は、ツールを使っている間 (マウスがビューの上) だけ Maya の「すべてをフレーム」/「すべてのビューで全体をフレーム」より先に取る。F (選択をフレーム) は効く
- 最後の点を消す (Delete) と、ガイドからは区間が消えるが、当てた切れ目は残る (Ctrl+Z なら一緒に戻る)
- 作成中に点を足すたびに UV が変わるので、UV の切れ目の表示 (段階 13) もそのたびに読み直す

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()
# A (自動) -> [作成] で点を足すたびに赤い切れ目 -> Ctrl+Z で点と切れ目が一緒に戻る / X (対称) なら両側
# Shift+A -> ボタンが「自動縫合」に -> 点を足すと縫合
```

mayapy (2027・2022) で、自動がオンなら 2 つ目の点で両側が切れる (UV 439 -> 443)・Ctrl+Z で点とカットが一緒に戻る・
オフなら UV は変わらないことを確かめた。
