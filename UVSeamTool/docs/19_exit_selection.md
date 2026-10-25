# 段階 19: ツールを抜けたらガイドのエッジを選ぶ

## 目的

ツールを抜けたとき、対象のメッシュの確定したガイドすべてのエッジを、エッジの選択モードで Maya の選択にする
(そのまま Maya の UV エディタなどで使えるように)。

| 抜けたときのモード | 動き |
|---|---|
| 作成・編集 | 作成中のガイドを確定してから (段階 5)、全部のガイドのエッジを選ぶ (選択は置き換え。エッジの選択モードにする) |
| 選択 | 何もしない (選んでいたエッジをそのまま残す。選択のモードの選択は、ユーザーが選んだものなので) |

ガイドが 1 本も無ければ選択を変えない。設定 `selectGuidesOnExit` (分類「ツールを抜けるとき」、既定オン) で止められる。

## 仕組み

```
toolOffCleanup
  3. サブツールの deactivate (作成中のガイドを確定)
     -> 作成・編集なら exit_selection.select_guides(対象のメッシュ)
          メッシュごとに、確定したガイドの seam_edges を集める
          enter_edge_mode (Undo に積まない) -> select_edges(置き換え。cmds.select = Undo に載る)
```

対称の相手も確定したガイドなので、一緒に選ばれる。

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [tool/exit_selection.py](../tool/exit_selection.py) | `select_guides(targets)` |
| [tool/context.py](../tool/context.py) | `toolOffCleanup` の 3 で呼ぶ |
| [core/settings/definitions.py](../core/settings/definitions.py) | `selectGuidesOnExit` |

## 落とし穴

- リロード (`reload_modules`) でもツールを抜けるので、作成・編集のモードならガイドのエッジが選ばれる
- 選んだエッジの番号はガイドの頂点の番号から求める。トポロジーが変わって使えないガイド (段階 6) は対象のメッシュの組に
  入っていないので選ばれない

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()
# [作成] でガイドを 2 本 -> Q (選択ツール) などで抜ける -> ガイドのエッジが選ばれ、エッジの選択モードになる
```

mayapy (2027・2022) で、確定したガイド (対称の相手も) のエッジだけが選ばれ (作成中のガイドは入らない)、
ガイドの無いメッシュ (立方体) は選ばれないことを確かめた。
