# 段階 18: 仕上げ

[目次](README.md) ・ 前: [段階 17](17_symmetry.md) ・ 次: [段階 19](19_ring_cut.md)

候補 (コンテキストの分割・使い方のページ・扱えないメッシュ・既存の継ぎ目・シェルフ・ボタンの置き場所・大きいメッシュ)
のうち、動きを変えずに保守しやすくする (1)、使う人が迷わない (2)、実際のシーンで壊れない (3) の 3 つを行った。

## 1. コンテキストの分割

`tool/context.py` が 960 行ほどになったので、役割ごとに分けた。動きは変えていない (テストはそのまま通る)。

| モジュール | 中身 |
|---|---|
| [tool/context.py](../tool/context.py) | ツール本体: 有効 / 無効・マウスの振り分け・パスのクリック・カット / 縫合 / クリア・操作の表・対象のメッシュ・外部の変更・設定のリスナー |
| [tool/selecting.py](../tool/selecting.py) `SelectingMixin` | 選択のモードの選択: クリック・ダブルクリック (1 回の Undo)・矩形・選んだエッジの反対側の表示 |
| [tool/symmetry.py](../tool/symmetry.py) `SymmetryMixin` | 対称: 面・効いているか・Maya の対称の変更・対応表・先に作る |
| [tool/command.py](../tool/command.py) | コンテキストのコマンド (フラグ)・ツールのコマンド・`delete_tool_context` |

- **ミックスイン**: `UVPathCutContext(SelectingMixin, SymmetryMixin, omui.MPxSelectionContext)`。部品はコンテキストの
  属性 (targets・settings・_manip など) と、互いのメソッドを使う。`__init__` は持たない (属性はコンテキストが作る)
- **プラグインはそのまま**: プラグインは `tool.context` から `UVPathCutContextCommand` / `ToolCommand` /
  `delete_tool_context` を引くので、context が command の名前を再び公開する。command の `makeObj` は context を
  呼ぶときに import する (context が command を import するので、循環を避ける)
- **リロードの順**: `selecting`・`symmetry`・`command` を `context` より前 (context が import する名前を新しくするため)

## 2. 使い方のページ

[USAGE.md](USAGE.md): 起動・2 つのモード・ボタンとキー・対称・ツール設定 (設定の表から確かめた一覧)・注意・
うまくいかないとき。目次 (README) の先頭からつないだ。あわせて、古くなっていた設定の説明 (モード・対称・プレビューの色)
を直した。

## 3. 扱えないメッシュ

mayapy で確かめた結果:

| メッシュ | カット / 縫合 | 対応 |
|---|---|---|
| シェイプがロック (lockNode) | 失敗。MDGModifier からは「Unexpected Internal Failure」としか分からない | 前もって調べ (`scene/mesh.edit_blocker`)、そのメッシュは実行せず理由を警告。自動カットは確定だけ |
| Transform だけロック | 成功 | 何もしない |
| リファレンス | 成功 | 何もしない |
| インスタンス | 成功 (形を共有するので、ほかのインスタンスも変わる) | 対象にしたときに知らせる (`mesh_notes`) |
| UV が無い | エラーにならないが意味がない | 対象にしたときに警告 |

| 場所 | 内容 |
|---|---|
| [scene/mesh.py:122](../scene/mesh.py#L122) `edit_blocker` / [:136](../scene/mesh.py#L136) `mesh_notes` | UV を変えられない理由 / 知らせること |
| [tool/context.py:398](../tool/context.py#L398) `_report_mesh` | ツールに入ったとき・対象に加えたときにログへ |
| [tool/context.py:403](../tool/context.py#L403) `_editable` / [:411](../tool/context.py#L411) `_editable_sessions` | まとめて実行・選択の実行で、変えられないメッシュを飛ばす |
| [tool/context.py:415](../tool/context.py#L415) `_run_edit` | シーンを変える関数の思わぬ失敗を、トレースバックではなく警告に (PathEditCommand が変更を戻し、Undo のキューにも積まない) |
| [tests/UVPathCut/mayapy/test_context.py:558](../../tests/UVPathCut/mayapy/test_context.py#L558) 〜 | 理由と知らせること・ロックしたメッシュを飛ばす・失敗の警告 |

## 試し方

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polySphere(name="a"); cmds.polySphere(name="b"); cmds.setAttr("b.translateX", 3)
cmds.lockNode("bShape", lock=True)
cmds.select("a", "b")
import UVPathCut; UVPathCut.tool()
# ログ: b について「シェイプがロックされています ... カット / 縫合はできません」
# b で区間を確定 (自動オン) -> 「確定だけして、カットはしません」
# a と b で区間をためて C -> a だけカットされ、b は警告
cmds.lockNode("bShape", lock=False)
```

ツールの使い勝手が今までどおりか (分割で壊れていないか) も、ひととおり触って確かめる。
