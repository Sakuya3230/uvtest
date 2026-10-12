# 段階 13: 外部の変更の検知

[目次](README.md) ・ 前: [段階 12](12_tool_settings_window.md) ・ 次: [段階 14](14_multiple_meshes.md)

## 目的

ツールを使っている間に、ツールの外でメッシュが変わっても、表示と計算を今のメッシュに合わせる。

| 外での変更の例 | 起きること | 対応 |
|---|---|---|
| チャンネルボックスで移動・スクリプトで頂点を動かす・再生で変形する | 位置が変わる | グラフの位置を入れ替える。区間はそのまま (エッジの番号は同じ) |
| スムーズ・押し出し・頂点の削除など (トポロジーの変更) | エッジの番号が別のものを指す | そのトポロジー用のセッションに切り替える。Undo で元に戻れば、前の区間が戻る |
| 自分のカット / 縫合・その Undo / Redo | UV だけが変わる | 何もしない (中身を比べて同じと分かる) |
| 名前の変更・親の変更 | フルパスが変わる | MDagPath で持ち、使うときに今の名前を読む |

## 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/sync.py](../core/sync.py) | 新規。Maya に依存しない判定とセッションの帳簿 |
| [core/sync.py:37](../core/sync.py#L37) `topology_key` | 面ごとの頂点の数と並びから、トポロジーの鍵 (数と hash) を作る |
| [core/sync.py:50](../core/sync.py#L50) `classify` | 前と今の鍵・位置から `CHANGE_NONE` / `CHANGE_POINTS` / `CHANGE_TOPOLOGY` |
| [core/sync.py:59](../core/sync.py#L59) `SessionBook` / [:78](../core/sync.py#L78) `sessionFor` | トポロジーの鍵ごとのセッション (最近の 4 つ)。`STATUS_SAME` / `NEW` / `RESTORED` |
| [core/graph.py:62](../core/graph.py#L62) `withPoints` | 位置だけ替えた新しいグラフ (エッジは同じ。Maya から読み直さない) |
| [core/graph.py:45](../core/graph.py#L45) `neighbors` | 隣接リストを使うときに作る (遅延)。長さは関数を呼ばない式で ([:37](../core/graph.py#L37)) |
| [core/session.py:138](../core/session.py#L138) `setGraph` | グラフを入れ替え、区間の長さを測り直し、スタートからの PathTree を作り直す |
| [scene/mesh.py:162](../scene/mesh.py#L162) | ワールドの行列の変更の通知 (`addWorldMatrixModifiedCallback`) も受け取る |
| [scene/mesh.py:173](../scene/mesh.py#L173) `_on_dirty` | 通知では「変わったかも」の印を付けるだけ |
| [scene/mesh.py:181](../scene/mesh.py#L181) `sync` | 印があれば、鍵と位置を比べてグラフを作り直し、変更の種類を返す |
| [scene/mesh.py:125](../scene/mesh.py#L125) `world_points` / [:130](../scene/mesh.py#L130) `mesh_topology_key` | 位置・鍵をまとめて読む (`getPoints` / `getVertices`) |
| [scene/mesh.py:169](../scene/mesh.py#L169) `name` | シェイプの今のフルパス (`MDagPath.fullPathName`) |
| [tool/context.py:360](../tool/context.py#L360) `syncMesh` | メッシュごとに `sync` → セッションを替える・ログ (段階 14 から `scene.targets.MeshTarget.sync`) |
| [tool/context.py:131](../tool/context.py#L131) `target` | 属性からプロパティへ (`name()`)。名前を変えられても追う |
| [tool/context.py:230](../tool/context.py#L230) / [:310](../tool/context.py#L310) | クリック・操作 (ボタン・キー) の前にも `syncMesh` |
| [tool/manipulator.py:104](../tool/manipulator.py#L104) `setSync` / [:166](../tool/manipulator.py#L166) / [:235](../tool/manipulator.py#L235) | マウスの移動 (doMove) と描く前 (preDrawUI) に `syncMesh` を呼ぶ |
| [tests/UVPathCut/test_sync.py](../../tests/UVPathCut/test_sync.py) | 鍵・判定・`withPoints`・`setGraph`・帳簿 (pytest 6 件) |
| [tests/UVPathCut/mayapy/test_mesh.py](../../tests/UVPathCut/mayapy/test_mesh.py) | `sync` の種類 (カット・頂点・Transform・スムーズと Undo)・名前の変更・削除中 (mayapy 3 件) |
| [tests/UVPathCut/mayapy/test_edit.py](../../tests/UVPathCut/mayapy/test_edit.py) | 確定 → スムーズ → Undo で前のセッションに戻り、確定の Undo がそのセッションに効く |

## 仕組み

### 通知と比べるのを分ける

```
Maya の通知 (シェイプの dirty / ワールドの行列)      ← 1 回のカットで何度も来る
  -> MeshModel._on_dirty: 印 (_changed) を付け、古い MFnMesh を捨てるだけ
描く前・マウスの移動・クリック・操作の前
  -> context.syncMesh -> MeshModel.sync
       印が無い                    -> CHANGE_NONE (何も読まない。0.005 ms)
       トポロジーの鍵が違う         -> CHANGE_TOPOLOGY: グラフを読み直す
       鍵が同じで位置が違う         -> CHANGE_POINTS: graph.withPoints(位置)
       どちらも同じ (UV のカットなど) -> CHANGE_NONE
  -> SessionBook.sessionFor(鍵, グラフ)
       同じセッション (位置が変わったならグラフを入れ替え) / 新しいセッション / 前のセッション
  -> manip.clearPick: 拾ったもの・プレビューを捨てて描き直す (段階 14 から)
```

通知の中では Maya を読まない (dirty の途中で読むと、評価を割り込ませることになる)。
重い比較は、使う直前に 1 回だけ行う。

### 旧版との違い

- **自分のカット / 縫合を特別扱いしない**。旧版は、自分のコマンドの間は通知を無視する印 (writing) を
  立てていた。今の版は中身を比べるので、UV の変更は「何も変わっていない」と分かる
  (比べるのに 4.5 万頂点で 20〜40 ms。カットのあと 1 回だけ)
- **トポロジーが変わっても区間を捨てない**。旧版はセッションを作り直していた。確定のコマンド
  (`PathEditCommand`) は自分のセッションを持っているので、トポロジーの鍵ごとにセッションを覚えておけば、
  Undo でトポロジーが戻ったときに前のセッションに戻り、確定の Undo / Redo もそのまま続けられる
- **名前の変更に強い**。旧版は対象をフルパスの文字列で持っていた。今は MDagPath から今の名前を読む

### トポロジーの鍵

エッジの番号は、面ごとの頂点の並びから Maya が決める。`MFnMesh.getVertices()` (面ごとの頂点の数と、
頂点の番号を並べたもの) が同じならエッジの番号も同じとみなし、(頂点の数・面の数・並びの長さ・hash) を鍵にする。
エッジの両端を 1 本ずつ読む (`getEdgeVertices`) より速い (4.5 万頂点で 8 ms と 60 ms)。

### 速さ (4.5 万頂点の球、2027)

| | 前 | 後 |
|---|---|---|
| 最初のグラフ | 136 ms | 74 ms |
| 位置の変更 (`sync`) | 128 ms | 57 ms |
| UV のカットのあと (`sync`) | | 20〜40 ms |
| トポロジーの変更 (`sync`) | | 300 ms ほど |
| 変わっていない (`sync`) | | 0.005 ms |

位置の変更で時間がかかっていたのは、隣接リスト (Python の A* だけが使う) を作り直す所だった。
使うときに作る (遅延) ようにし、長さの計算も関数を呼ばない式にした。numpy で長さを計算すると、
リストとの変換のほうが重くて遅くなった (65 ms と 40 ms)。

## 落とし穴

- Transform を動かしても、シェイプは dirty にならないことがある。ワールドの行列の変更の通知
  (`MDagMessage.addWorldMatrixModifiedCallback`。親の移動でも来る) も受け取る
- メッシュが消えている間は調べない (印は残す)。Undo で戻ってから調べる
- 描いている途中 (`preDrawUI`) では拾い直さない (`view.refresh` を呼ぶことになるため)。拾ったものを
  捨てておき、次にマウスを動かしたときに拾い直す
- 再生でスキンのメッシュが毎フレーム変形すると、毎フレーム `withPoints` (50 ms ほど) が走る
- 新しいトポロジーのセッションにはスタートが無い (古い番号は別のものを指すため)

## 試し方

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polySphere(name="ball")
import UVPathCut; UVPathCut.tool()
# 1. 区間を 1 つ確定し、スタートを置いたまま、チャンネルボックスで ball の移動 X を変える
#    -> 区間・スタートが一緒に動く (マウスを動かすと、プレビューも新しい位置で出る)
# 2. スクリプトエディタで cmds.polySmooth("ball")
#    -> 「トポロジーが変わりました」の警告。区間の表示が消える (新しいトポロジーでは空)
# 3. Ctrl+Z (スムーズの Undo) -> 「前のトポロジーに戻ったので…」で、区間が戻る
#    もう一度 Ctrl+Z -> 確定の Undo が効いて区間が 1 つ戻る
# 4. cmds.rename("ball", "orb") のあと確定・カットしても動く
```
