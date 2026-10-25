# 段階 3: ガイドの組と Undo

## 目的

作ったガイドをメッシュごとの組に残し、どの操作も Ctrl+Z で 1 つずつ戻せるようにする。カットはガイドと別の操作にする。

| 操作 | 動き | Ctrl+Z |
|---|---|---|
| 左クリック | 作成中のガイドに点を足す (無ければ新しいガイドを始める) | 1 回で 1 点戻る |
| Delete / Backspace | 最後の点を消す (1 点だけならガイドごと) | 戻る |
| Enter | 作成中のガイドを確定する (カットはしない。点が 1 つなら捨てる) | 戻る (作成中に戻る) |
| Esc | 作成中のガイドを捨てる | 戻る |
| `UVSeamTool.cut_guides()` / `sew_guides()` | 確定したガイドすべてのエッジでカット / 縫合 | polyMapCut / polyMapSew の Undo (ガイドは残る) |

確定したガイドは水色、作成中のガイドはマゼンタで描く (今は確定がマゼンタ・作成中が橙。[07a_settings.md](07a_settings.md) の最後)。

## 決めたこと (ユーザーの選択)

- Enter はガイドを確定するだけ。カット / 縫合は別の操作 (今は api の関数。キー・ボタンは後の段階)
- Ctrl+Z は点ごと (点を足す・最後の点を消す・確定・捨てるが、どれも 1 回の Undo)

## 流れ

```
左クリック
  -> CreateTool.press
     -> set_editing.add_point(今の組, graph, vertex)       (core) 新しい組を作る (元の組は変えない)
     -> guide_edit.apply(key, 新しい組)                    (tool)
        -> undo.run(redo, undo)                            (utils) モジュールに関数を置いて uvSeamToolEdit を呼ぶ
           -> UndoCommand.doIt -> redo()                   store.setGuideSet(key, 新しい組)
              -> GuideStore のリスナー -> Context._on_guides_changed -> CreateTool.refresh -> view.refresh
Ctrl+Z
  -> UndoCommand.undoIt -> undo()                          store.setGuideSet(key, 前の組) -> 同じリスナー
```

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [core/guide/guide_set.py](../core/guide/guide_set.py) | `GuideSet`: メッシュ 1 つのガイドの組 (変えられない値)。作成中のガイドも `guides` に入れて `active_id` で指す |
| [core/guide/set_editing.py](../core/guide/set_editing.py) | 組の編集 `add_point` / `remove_last_point` / `finish_active` / `discard_active`。新しい組を返し、何も変わらなければ None |
| [core/guide/editing.py](../core/guide/editing.py) | `remove_last_point(guide)` を足した |
| [core/guide/guide_store.py](../core/guide/guide_store.py) | `GuideStore`: メッシュの鍵 -> 今の組。変わったらリスナーに知らせる。`store()` でパッケージに 1 つ |
| [core/path/path_preview.py](../core/path/path_preview.py) | `PathPreview`: 同じ始点の PathTree を使い回す (前の `GuideCreation.previewTo` の役目) |
| [utils/undo.py](../utils/undo.py) | `UndoCommand` (MPxCommand) と `run(redo, undo)` |
| [utils/mesh.py](../utils/mesh.py) | `key()`: MObjectHandle の hashCode (名前を変えても変わらない) |
| [tool/guide_edit.py](../tool/guide_edit.py) | `apply(key, new_set)`: 前の組と新しい組を `undo.run` に渡す |
| [tool/create_tool.py](../tool/create_tool.py) | 組を編集して `guide_edit.apply`。確定したガイドも描く |
| [tool/context.py](../tool/context.py) | 置き場所のリスナーで描き直す (Undo / Redo でも) |
| [plug-ins/uvSeamTool.py](../../../plug-ins/uvSeamTool.py) | `uvSeamToolEdit` を登録 |
| [api.py](../api.py) | `cut_guides` / `sew_guides`。`load_plugin` はコマンドが足りなければプラグインを読み直す |
| [reloader.py](../reloader.py) | リロードの前に Undo の履歴を消す |

`core/guide/guide_creation.py` (`GuideCreation`) は消した。点を足す前のガイドを自分で積んでいたが、Undo が同じ役目をするため。

## 仕組み

- **Undo は「組の前と後を入れ替える」だけ**: 組は変えられない値なので、操作の前の組と後の組を持っておけば、
  undoIt は前の組を、redoIt は後の組を置き場所に入れるだけ。点を足す・消す・確定・捨てるのどれも同じコマンド 1 種類
  (後で足す点の移動・挿入なども同じ)
- **関数をコマンドに渡す**: MPxCommand の引数には Python の関数を渡せない。`undo.run` がモジュールの `_pending` に
  (redo, undo) を置いてからコマンドを呼び、`doIt` が受け取って自分で持つ
- **表示は置き場所を見るだけ**: `CreateTool` は組を持たず、描くたびに `guide_store` から引く。Undo / Redo で組が
  変わるとリスナーが呼ばれ、プレビューを作り直して描き直す
- **カットはガイドを変えない**: `cut_guides` はガイドからエッジを求めて polyMapCut を呼ぶだけ。カットを Undo しても
  ガイドは残る

## 落とし穴

- ガイドの置き場所はモジュールの中にある (シーンに保存していない)。**Maya を閉じる・リロードすると消える**
  (保存は U60 で相談)
- リロードすると置き場所が新しく空になるので、前の Undo の履歴を残すと、戻したときに古い置き場所を書き換える
  (表示とずれる)。`reload_modules()` は Undo の履歴を消す
- プラグインにコマンドを足したので、前の段階のプラグインを読み込んだままの Maya では `load_plugin()` が
  読み直す (Undo の履歴は消える)
- Undo の中身は Python の関数なので、Maya の Undo の一覧にはコマンドの名前 (`uvSeamToolEdit`) だけが出る
- メッシュの鍵は hashCode。Maya を開き直すと変わる (保存するときは別の鍵が要る)

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere()
UVSeamTool.tool()
# クリックで 3 点 -> Ctrl+Z で 1 点ずつ戻る -> Ctrl+Y (やり直し) で戻る
# Enter で確定 (マゼンタになる) -> もう一度クリックで 2 本目のガイドが始まる
UVSeamTool.cut_guides()   # 確定したガイドでカット (UV エディタで見る)。Ctrl+Z でカットだけ戻る
```

mayapy (2022 / 2027) で、点を足す・消す・確定の Undo / Redo と、カットの Undo のあともガイドが残ることを確かめた。

## 追加: 右クリックで確定

(段階 5b で `RightClickFilter` (`tool/right_click.py`) は、ドラッグ中の Esc も受け取る `ViewInputFilter` (`tool/view_input.py`) に広げた。[05b_move_points.md](05b_move_points.md))

作成中のガイドがあるときに、ビューの右クリックでも確定する (Enter と同じ)。作成中のガイドが無ければ、
いつもどおりマーキングメニューが出る。

### なぜ Qt のイベントフィルターか

コンテキストが受け取るマウスのボタン (`MEvent`) は `kLeftMouse` / `kMiddleMouse` だけで、右ボタンが無い
(API 2.0 のスタブで確認)。ビューの右クリックは Maya がマーキングメニューに使い、コンテキストの `doPress` に届かない。
そこで、アプリ全体の Qt のイベントフィルターで、Maya より先に受け取る。

```
右ボタンを押す (3D のビューの描画面の上)
  -> RightClickFilter.eventFilter               (tool/right_click.py。QApplication に付ける)
     -> ビューの描画面か (ポインタで比べる)      utils.view.view_widget_pointers / compat.qt.pointer_of
     -> Context._on_right_click -> CreateTool.rightClick
        作成中のガイドがあれば complete() して True -> 押したイベントと、次の離したイベントを Maya に渡さない
        無ければ False -> 何もしない (マーキングメニュー)
```

| ファイル | 中身 |
|---|---|
| [compat/qt.py](../compat/qt.py) | PySide6 / PySide2 の違い (`QtCore` / `QtGui` / `QtWidgets`・`wrap_instance`・`pointer_of`) |
| [tool/right_click.py](../tool/right_click.py) | `RightClickFilter` |
| [utils/view.py](../utils/view.py) | `view_widget_pointers()`: 3D のビューの描画面のポインタの集合 |
| [tool/sub_tool.py](../tool/sub_tool.py) / [tool/create_tool.py](../tool/create_tool.py) | `rightClick()` |
| [tool/context.py](../tool/context.py) | ツールを有効にしたときにフィルターを付け、抜けるときに外す |

### 落とし穴

- ウィジェットは `==` ではなく C++ のポインタで比べる (shiboken のラッパーは同じウィジェットでも別のものになることがある。
  ViewPanelLesson と同じ)
- 押したのを受け取ったら、対になる離したイベントも渡さない (片方だけ渡すと、Maya の側の右ボタンの状態がずれる)
- フィルターは必ず `toolOffCleanup` で外す (外さないと、ツールを抜けても右クリックを取り続ける)
- mayapy で Qt を試すときは、`maya.standalone.initialize()` より **前に** QApplication を作る (後に作るとプロセスごと落ちた)
