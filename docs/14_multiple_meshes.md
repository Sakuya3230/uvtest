# 段階 14: 複数のメッシュ

[目次](README.md) ・ 前: [段階 13](13_external_changes.md) ・ 次: [段階 15](15_straightness.md)

## 目的

段階 13 までは、ツールを有効にしたときの最初のメッシュ 1 つだけが対象で、選択を変えても
ツールを入れ直すまで前のメッシュを使い続けていた。これを、複数のメッシュを同時に扱えるようにする。

- 対象 = ツールを有効にしたときに選んでいる / ハイライトしているメッシュすべて。ツールを使っている間に
  選んだメッシュも加わる (ツールを入れ直すまで増えるだけ)
- ホバーは、対象すべてのうちいちばん手前の面で拾う
- パスは 1 つのメッシュの中だけ。スタートと違うメッシュをクリックすると、そこが新しいスタート
- 区間はメッシュごとに覚える。確定の選択・まとめてカット / 縫合・クリアは全メッシュが対象 (どれも 1 回の Undo)

## 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [scene/targets.py](../scene/targets.py) | 新規。対象のメッシュの集まり |
| [scene/targets.py:35](../scene/targets.py#L35) `MeshTarget` | メッシュ 1 つ = MeshModel + SessionBook (段階 13 でコンテキストが 1 つずつ持っていたもの) |
| [scene/targets.py:58](../scene/targets.py#L58) `session(create)` | 今のトポロジーのセッション。グラフは初めてクリックしたときに作る |
| [scene/targets.py:83](../scene/targets.py#L83) `TargetSet` / [:126](../scene/targets.py#L126) `add` / [:104](../scene/targets.py#L104) `setShapes` | 対象 (active) と、一度でも対象にしたもの (known)。見分けは MObjectHandle |
| [scene/targets.py:157](../scene/targets.py#L157) `hit` | 対象すべてにレイを当て、始点にいちばん近い交点のメッシュ |
| [scene/targets.py:141](../scene/targets.py#L141) `sessions` / [:150](../scene/targets.py#L150) `owner` / [:171](../scene/targets.py#L171) `sync` | セッションのある対象 / セッションの持ち主 / 外部の変更をメッシュごとに |
| [scene/mesh.py:66](../scene/mesh.py#L66) `target_meshes` | 選択 (選んだ順) とハイライトのメッシュすべて |
| [scene/edit.py:69](../scene/edit.py#L69) `edges_selection` | メッシュごとのエッジを 1 つの選択に |
| [scene/edit.py:246](../scene/edit.py#L246) `confirm_path(others=)` | ほかのメッシュの区間のエッジも選んだままにする |
| [scene/edit.py:284](../scene/edit.py#L284) `apply_pending_all` / [:323](../scene/edit.py#L323) `clear_sessions` | 全メッシュをまとめて 1 回の Undo で (UVChange はメッシュごと) |
| [scene/edit.py](../scene/edit.py) `PathEditCommand` | 変えたセッションをリストで持ち、全部に知らせる |
| [core/sync.py:78](../core/sync.py#L78) `sessions` | 帳簿の覚えているセッションすべて (リスナーを外すため) |
| [tool/context.py:141](../tool/context.py#L141) `toolOnSetup` / [:186](../tool/context.py#L186) `_new_session` | 対象すべてをエッジの選択モードに。セッションは作るときにリスナーを付ける |
| [tool/context.py:221](../tool/context.py#L221) `_click` / [:256](../tool/context.py#L256) `_clear_start` | 別のメッシュならスタートを移す (スタートは全体で 1 つ = `start_target`) |
| [tool/context.py:263](../tool/context.py#L263) `_other_edges` | 確定のとき、ほかのメッシュの区間のエッジ |
| [tool/context.py:268](../tool/context.py#L268) `applyPending` / [:281](../tool/context.py#L281) `clearAll` / [:299](../tool/context.py#L299) `actionState` | 全メッシュが対象・合計 |
| [tool/context.py:323](../tool/context.py#L323) `_on_selection_changed` / [:329](../tool/context.py#L329) `updateTargets` | 選択の変更 → 手すきのときに対象を加え、ハイライトを付け直す |
| [tool/context.py:387](../tool/context.py#L387) `_on_session_changed` | Undo で別のメッシュのスタートが戻ったら、そちらをスタートにする |
| [tool/manipulator.py:111](../tool/manipulator.py#L111) `setTargets` / [:117](../tool/manipulator.py#L117) `clearPick` / [:150](../tool/manipulator.py#L150) `pickTarget` | 対象の集まりを持ち、どのメッシュで拾ったかも持つ |
| [tool/manipulator.py:178](../tool/manipulator.py#L178) / [:252](../tool/manipulator.py#L252) | いちばん手前のメッシュで拾う / 全メッシュの区間を描く |
| [tests/UVPathCut/mayapy/test_targets.py](../../tests/UVPathCut/mayapy/test_targets.py) | 対象の一覧・増減と記憶・手前のメッシュ・メッシュごとの変更 (4 件) |
| [tests/UVPathCut/mayapy/test_context.py](../../tests/UVPathCut/mayapy/test_context.py) | コンテキストの流れ (スタートの移動・全メッシュの実行とクリア・Undo とスタート・対象の追加。5 件) |
| [tests/UVPathCut/mayapy/test_edit.py](../../tests/UVPathCut/mayapy/test_edit.py) | 2 つのメッシュの確定の選択・まとめてカット・クリアと Undo |

## 仕組み

### 対象の持ち方

```
TargetSet
  active: [MeshTarget, ...]   今の対象 (消えたメッシュも残し、valid() が飛ばす)
  known:  [MeshTarget, ...]   一度でも対象にしたもの
MeshTarget
  model  MeshModel     面・グラフ・外部の変更 (段階 3〜13)
  book   SessionBook   トポロジーごとのセッション (段階 13)。初めてクリックしたときに作る
コンテキスト
  start_target   スタートを置いたメッシュ (スタートは全体で 1 つ)
```

段階 13 で作った「トポロジーごとのセッション」を、そのまま「メッシュごと × トポロジーごと」に広げた。
確定のコマンドは自分のセッションを持っているので、どのメッシュの Undo / Redo でも正しいセッションに効く。

### 見分け方は MObjectHandle

Maya を起動している間、同じノードなら同じ (名前を変えても同じ)。比べるのも速い。
UUID はシーンに保存されて残るが、読み込み方によっては重なることがあるので、ツールを抜けても
覚えておくキャッシュ (段階 16 のシンメトリの対応表など) の鍵に使う。形のハッシュは、複製した
同じ形のメッシュを区別できないので使わない。

### 対象が増えるとき

```
選択が変わる (Maya の SelectionChanged)
  -> _on_selection_changed: executeDeferred で 1 回だけ予約 (通知の中ではシーンを変えない)
  -> updateTargets (手すきのとき)
       target_meshes() の新しいメッシュを対象に加える (TargetSet.add)
       対象のうちハイライトが外れたものを、エッジの選択モードに戻す (Undo には積まない)
```

自分の確定・カットでも選択は変わるが、選ぶのは対象のメッシュのエッジなので何も増えない。

### スタートは全体で 1 つ

- 別のメッシュをクリックすると、前のスタートを外してそこをスタートにする (またぐパスは無い)
- Undo で別のメッシュのスタートが戻った (左で確定 → 右にスタート → Ctrl+Z) ときは、
  `_on_session_changed` が戻ったほうをスタートにして、もう一方を外す
- プレビューはスタートと同じメッシュの上だけ (別のメッシュの上では番号だけを出す)

## 落とし穴

- オブジェクトの選択モードで別のメッシュを選ぶと、前のメッシュのハイライトが外れる (mayapy で確認)。
  ハイライトを対象にすると、前のメッシュが対象から外れてしまう。そこで対象はツールを入れ直すまで
  増えるだけにし、外れたハイライトは付け直す
- 選択の変更の通知の中でハイライト (シーンの状態) を変えない。`maya.utils.executeDeferred` で後にする
- ハイライトの付け直しは Undo に積まない (`undoInfo(stateWithoutFlush=False)`)。積むと Ctrl+Z が
  ハイライトを戻すだけになる
- 番号はメッシュごとなので、拾ったものが変わったかの目印にメッシュも入れる
- グラフは初めてクリックしたときに作る。ホバーにはグラフが要らない

## 試し方

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polySphere(name="left"); cmds.polySphere(name="right"); cmds.setAttr("right.translateX", 3)
cmds.select("left", "right")
import UVPathCut; UVPathCut.tool()
# 1. 両方のメッシュの上でホバー・確定ができる (左で 2 回クリック、右で 2 回クリック)
#    -> 右をクリックしたとき、左のスタートが外れて右がスタート。選択は両方の区間のエッジ
# 2. C (まとめてカット) -> 両方が 1 回の Undo でカットされる。Ctrl+Z で両方が戻る
# 3. Shift+Esc (クリア) -> 両方の区間が外れる。Ctrl+Z で戻る
# 4. ツールのまま、アウトライナーで別のメッシュを選ぶ -> 「対象に加えました」。前のメッシュも対象のまま
```
