# 段階 8: 確定と Undo

[目次](README.md) ・ 前: [段階 7](07_click_and_session.md)

## 目的

- 2 回目以降のクリックでパスを **確定** する。1 回の Undo で次の 3 つをまとめて行う
  1. 確定した区間をスタックに積む
  2. エンドを次のスタートにする
  3. 確定した区間すべてのエッジを選ぶ (ツールを抜けても、エッジの選択だけが残る)
- Ctrl+Z 1 回で 1 区間ぶん戻る (区間・スタート・選択がそろって戻る)
- 「変更のリストを 1 回の Undo で行うコマンド」を汎用の形で作る (段階 9 のカット / 縫合も同じコマンドに乗せる)

スタートを決めるだけのクリックは Undo に積まない。

## 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/session.py:48](../core/session.py#L48) `PathSegment` | 確定した 1 区間 (スタート・エンド・エッジ・頂点・長さ) |
| [core/session.py:88](../core/session.py#L88) `push` / `pop` / [:94](../core/session.py#L94) `edges` | 区間のスタック / 区間のエッジ (重複なし、確定した順) |
| [core/session.py:107](../core/session.py#L107) `addListener` / [:116](../core/session.py#L116) `notify` | セッションが変わったことを知らせる |
| [scene/edit.py:45](../scene/edit.py#L45) `ConfirmChange` | 確定で変わるもの (区間・スタート・選択) の redo / undo |
| [scene/edit.py:68](../scene/edit.py#L68) `PathEditCommand` | 変更のリストを 1 回の Undo で行うコマンド `uvPathCutEdit` |
| [scene/edit.py:112](../scene/edit.py#L112) `run_changes` | `_PENDING` に置いて MEL で `uvPathCutEdit -n "<名前>"` を呼ぶ |
| [scene/edit.py:122](../scene/edit.py#L122) `confirm_path` | スタートからゴールまでを確定する |
| [scene/edit.py:34](../scene/edit.py#L34) `edge_selection` | エッジだけの MSelectionList |
| [core/draw_list.py:166](../core/draw_list.py#L166) `segment_items` | 確定した区間 (未実行はマゼンタ。段階 10 の後に水色から変えた) と区間の両端の印 |
| [tool/context.py:164](../tool/context.py#L164) | 2 回目以降のクリックで `confirm_path` |
| [tool/context.py:100](../tool/context.py#L100) / [:173](../tool/context.py#L173) `_on_session_changed` | セッションのリスナーで表示を更新 (確定・Undo・Redo のどれでも) |
| [plug-ins/uvPathCut.py:79](../../../plug-ins/uvPathCut.py#L79) | `uvPathCutEdit` を登録 (creator は [_create_edit_command:54](../../../plug-ins/uvPathCut.py#L54)。クラスを毎回引く) |
| [constants.py](../constants.py) | `EDIT_COMMAND` |
| [tests/UVPathCut/mayapy/test_edit.py](../../tests/UVPathCut/mayapy/test_edit.py) | 確定・Undo・Redo・ツールを抜けたあとの Undo (mayapy 4 件) |
| [tests/UVPathCut/test_session.py](../../tests/UVPathCut/test_session.py) / [test_draw_list.py](../../tests/UVPathCut/test_draw_list.py) | 区間・リスナー・区間の描画 (pytest 3 件) |

## 仕組み

### 変更のリストを 1 回の Undo で行う

```
confirm_path(session, shape, goal)
  -> 変更のリスト [ConfirmChange(区間, 前後のスタート, 前後の選択)]
  -> run_changes(session, 変更, "UV パスの確定 (12 本)")
       _PENDING = [(session, 変更)]                      Python のオブジェクトはコマンドの引数で渡せない
       mel.eval('uvPathCutEdit -n "UV パスの確定 (12 本)"')
         -> PathEditCommand.doIt   _PENDING を受け取り、redoIt
         -> redoIt                 変更を順に redo -> session.notify()
Ctrl+Z  -> undoIt                  変更を逆の順に undo -> session.notify()
Ctrl+Y  -> redoIt
```

- `isUndoable()` が True のコマンドは、Maya の Undo のキューに積まれる。Undo / Redo のときに
  Maya が `undoIt` / `redoIt` を呼ぶ。コマンドのインスタンスは変更のリストを持ち続ける
- 途中で失敗したら、行った分を逆の順に戻してから例外を投げる (中途半端に変わらない)
- Undo の記録の名前は「実行した MEL の文字列」。Python の cmds で呼ぶと空になるので、MEL で
  `-n` を付けて呼ぶ (「Undo: uvPathCutEdit -n "UV パスの確定 (12 本)"」と出る)

### 選択も戻す

`MGlobal.setActiveSelectionList` は、それ自身では Undo に載らない。そこで変える前の選択
(`getActiveSelectionList`) を覚えておき、undo で戻す。段階 9 で、選択の変更は `SelectionChange` に
分けた (コマンドがいつも最後に行う。polyMapCut が途中で選択を変えるため。段階 9 の落とし穴)。

### 表示の更新はリスナーで

```
PathEditCommand.redoIt / undoIt -> session.notify()
  -> UVPathCutContext._on_session_changed -> refresh (プレビューを引き直して描き直す)
```

旧版はコマンドが「使っているコンテキスト」を探して更新していた (`_ACTIVE`)。今はセッションが
リスナーに知らせるだけなので、コマンド (scene) は表示 (tool) のことを知らない (依存の向き
`tool -> scene -> core` を守れる)。ツールを抜けるときにリスナーを外すので、抜けたあとの Undo は
表示されていないセッションを変えるだけで、選択だけが目に見えて戻る。

## 落とし穴

- `MGlobal.setActiveSelectionList` は Undo に載らない (自分で前の選択を戻す)
- Python の cmds でコマンドを呼ぶと、Undo の記録の名前が空になる (MEL で -n を付けて呼ぶ)
- コマンドを直接 (ツールの外から) 呼ぶと、`_PENDING` が空なのでエラーにする
- **コマンドを足したら、プラグインを読み直さないと登録されない** (登録は `initializePlugin` のときだけ)。
  段階 7 のプラグインのままリロードしたら、2 回目のクリックで「Cannot find procedure "uvPathCutEdit"」に
  なった。今は `reload_modules` の最後に `api.ensure_plugin_current` が、`constants.PLUGIN_COMMANDS` /
  `PLUGIN_NODES` がそろっているかを確かめ、足りなければプラグインを読み直す (Undo の履歴は消える)。
  コマンド・ノードを足したら、`constants` の一覧にも足すこと。確かめるのは `hasattr(cmds, 名前)`
  (`pluginInfo -command` にはコンテキストのコマンドが出ない。`cmds.exists` は Python には無い)
- リロードしても、Undo のキューに残ったコマンドは作ったときのクラスのまま動く (古いコードで
  Undo される)。仕組みを変えたあとは、念のため新しいシーンで試す

## 試し方

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polySphere()
import UVPathCut; UVPathCut.tool()
# 1. クリック 2 回: 区間がマゼンタになり、そのエッジが選ばれる。3 回目以降は選択が積み重なる
# 2. Ctrl+Z: 1 区間ぶん戻る (マゼンタの線・選択・緑のスタート)。Ctrl+Y でやり直す
# 3. Esc で切ってから別の所で始めても、前の区間 (マゼンタ) は残る
# 4. ツールを抜けると表示は消え、エッジの選択だけが残る。抜けたあとの Ctrl+Z で選択が戻る
```
