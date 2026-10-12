# 段階 9: カット / 縫合・自動カット・まとめて実行

[目次](README.md) ・ 前: [段階 8](08_confirm_and_undo.md)

## 目的

- 確定した区間のエッジで、UV を **カット** (polyMapCut) / **縫合** (polyMapSew) する
- **自動カット** (設定 `autoCut`、既定オン): 確定と同時に設定 `operation` の操作を行う。確定と実行を合わせて Undo 1 回
- **自動カットなし**: 確定は区間をためるだけ。ためた区間を **まとめて実行** する (Undo 1 回。Undo すると UV だけが戻り、確定した区間は残る)
- 区間の色を状態で分ける (未実行 マゼンタ / カット 赤 / 縫合 緑。段階 10 の後に、未実行を水色からマゼンタに変えた)

まとめて実行は、この段階ではコンテキストのコマンドのフラグ `-apply cut / sew` から
(ボタンとキーは段階 10・11)。

## 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/components.py](../core/components.py) `index_ranges` / `edge_component_names` | 続いている番号を範囲 (`e[3:7]`) にまとめる / エッジの名前の一覧 |
| [core/session.py:27](../core/session.py#L27) `OPERATION_CUT` など | 操作の名前と表示名 |
| [core/session.py:66](../core/session.py#L66) `PathSegment.operation` | 実行した操作 (まだなら None) |
| [core/session.py:116](../core/session.py#L116) `pendingSegments` | まだ実行していない区間 |
| [scene/edit.py:80](../scene/edit.py#L80) `UVChange` | `MDGModifier.commandToExecute("polyMapCut ...")` で実行し、`undoIt` で戻す |
| [scene/edit.py:101](../scene/edit.py#L101) `OperationChange` | 区間に実行した操作の印を付ける / 外す |
| [scene/edit.py:172](../scene/edit.py#L172) `confirm_path(..., operation)` | 自動カットなら、確定と同じ Undo に `UVChange` と `OperationChange` を足す |
| [scene/edit.py:200](../scene/edit.py#L200) `apply_pending` | ためた区間をまとめて実行する (1 回の Undo) |
| [core/draw_list.py:75](../core/draw_list.py#L75) `SEGMENT_ROLES` / `ROLE_CUT` / `ROLE_SEW` | 区間の状態 → 色 |
| [tool/context.py:170](../tool/context.py#L170) | 確定のときに、自動カットなら設定の操作を渡す |
| [tool/context.py:181](../tool/context.py#L181) `applyPending` / [:65](../tool/context.py#L65) `APPLY_FLAG` | まとめて実行 / `-apply cut / sew` |
| [tests/UVPathCut/test_components.py](../../tests/UVPathCut/test_components.py) | 範囲のまとめ方・未実行の区間・色 (pytest 4 件) |
| [tests/UVPathCut/mayapy/test_edit.py](../../tests/UVPathCut/mayapy/test_edit.py) | 自動カットの Undo (ヒストリーの有無)・まとめて実行・縫合 (mayapy 2 件) |

## 仕組み

### UV を変える変更 (UVChange)

```python
modifier = om.MDGModifier()
modifier.commandToExecute('polyMapCut "|ball|ballShape.e[84:96]" "|ball|ballShape.e[108]"')
modifier.doIt()     # 実行する (redo)
modifier.undoIt()   # 取り消す (undo)
```

`MDGModifier` は「まとめて行い、まとめて取り消せる DG の変更」の入れ物。`commandToExecute` は
MEL のコマンドを 1 つ足す (そのコマンド自体が Undo できることが条件。polyMapCut / polyMapSew はできる)。
`undoIt` で polyMapCut のノードが消え、ヒストリーの無いメッシュも元に戻る。もう一度 `doIt` すれば
やり直せる (旧版の mayapy で確認)。エッジは続いている番号を範囲にまとめて、コマンドの文字列を短くする。

### 1 回の Undo にまとめるもの

| 操作 | 変更のリスト (この順に redo、逆順に undo) | Undo の名前 |
|---|---|---|
| 確定 (自動カットなし) | `ConfirmChange` → `SelectionChange` | UV パスの確定 (12 本) |
| 確定 (自動カット) | `ConfirmChange` → `UVChange` → `OperationChange` → `SelectionChange` | UV パスの確定とカット (12 本) |
| まとめて実行 | `UVChange` → `OperationChange` → `SelectionChange` (前と同じ選択) | UV パスのカット (2 区間 / 24 本) |

`SelectionChange` は `final = True` で、コマンドはこれを redo でも undo でも最後に行う (下の落とし穴)。

段階 8 で作った「変更のリストを 1 回の Undo で行うコマンド」に、変更を足すだけで済んでいる。

### 区間の状態

`PathSegment.operation` は None (未実行) / "cut" / "sew"。`OperationChange` が付け外しする
(Undo すれば未実行に戻る)。まとめて実行は未実行の区間 (`pendingSegments`) だけを対象にするので、
2 回押しても同じエッジを 2 回カットしない。色は `SEGMENT_ROLES` で状態から役割を引く。

## 落とし穴

- **ヒストリーのあるメッシュをカットしたあと、前に作った MFnMesh を使うと Maya が落ちる**。
  段階 3 の `MeshModel` が dirty で作り直すので、ここでは起きない (テストでカットのあとに MeshModel を使って確かめている)
- UV の数でカットを確かめない。もとの UV の継ぎ目と重なる道をカットしても UV は増えない
  (旧版のテストで、`polySphere` の頂点 0 の経線がそうだった)。テストは polyMapCut / polyMapSew の
  ノードの `inputComponents` (対象のエッジ) で確かめる
- **polyMapCut / polyMapSew は、エッジを選んでいると対象のエッジを選択にしてしまう**。自動カットで
  2 区間目を確定すると、全区間ではなく 2 区間目のエッジだけが選ばれていた (GUI で発見、mayapy で再現)。
  旧版で「選択を変えない」と確かめたのは、オブジェクトを選んだ状態だった。選択の変更を
  `SelectionChange` に分け、コマンドがいつも最後に行う (undo でも最後に戻す) ようにした。
  まとめて実行も、実行の前の選択に決め直す
- `listHistory` に `type` のフラグは無い。`cmds.ls(cmds.listHistory(shape), type="polyMapCut")` で絞る

## 試し方

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polySphere()
import UVPathCut; UVPathCut.tool()
ctx = "uvPathCutContext"
# 1. 自動カット (既定): 2 回目のクリックで区間が赤くなり、UV エディタ (テクスチャの境界の表示) で切れている
#    Ctrl+Z 1 回で、カットも確定 (赤い線・選択・スタート) も戻る
# 2. 縫合を自動にする
cmds.uvPathCutCtx(ctx, edit=True, operation="sew")
# 3. ためてからまとめて実行
cmds.uvPathCutCtx(ctx, edit=True, autoCut=False)   # 確定してもマゼンタのまま (UV は変わらない)
cmds.uvPathCutCtx(ctx, edit=True, apply="cut")     # マゼンタが全部赤になって切れる。Ctrl+Z でカットだけ戻る
```
