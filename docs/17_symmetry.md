# 段階 17: シンメトリ

[目次](README.md) ・ 前: [段階 16](16_select_mode.md) ・ 次: [段階 18](18_finishing.md)

| | 内容 | 状態 |
|---|---|---|
| 17a | 対応表 (MirrorMap)・対称の面・設定・使い回し A / B / C | 実装済み |
| 17b | パスのモード: 区間の反対側・両側のカット / 縫合 / 選択・反対側の描画 | 実装済み |
| 17c | 選択のモード: 反対側を足したカット / 縫合・覆われた区間・反対側の描画 | 実装済み |
| 17d | ボタン「対称 X / OFF」(両方のモード)・X キー・ヘルプライン | 実装済み |

## 決めた仕様

- ツールの設定「対称」(既定オフ) で、どちらのモードでも反対側を足す。Maya の対称の選択
  (`setAllowSymmetry`) は使わない (どちらが効いているか分かりにくくなるため。ツールの対称に一本化)
- 対称の面: **Maya の対称 (symmetricModelling) がオンでワールド / オブジェクトなら Maya の面** (空間・軸・許容値)。
  このときはツールの「対称」がオフでも両側に効く。オフ (かトポロジー) なら、ツールの設定「空間」「軸」「許容値」。
  どちらを使っているかは、ツール設定のウィンドウ (空間・軸・許容値を灰色にし「Maya の対称: ワールド Z  許容値 0.1」) で見せる
- 経緯: (1) はじめは Maya 優先 → (2) 17b の確認で「ツール設定と食い違って分かりにくい」ので、ツールの設定だけに →
  (3) 17c の確認で、Maya の対称がオンだと選択のモードの **選択そのものを Maya が両側にしてしまい**、ツールの対称
  (X) と Maya の対称 (Z) が二重にかかった。API に選択の対称を切る方法は無い (`setAllowSymmetry` は有効にするだけ) ので、
  ツールの中で面を 1 つにそろえるため、両方のモードで Maya 優先にし、表示で分かるようにした
- 反対側は位置で決める。頂点を面で鏡映した点から、許容値の中で最も近い頂点。エッジは両端の反対側を結ぶエッジ
- 対応表は使い回す (旧版の A・B・C)

## 17a: 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/mirror.py:47](../core/mirror.py#L47) `MirrorMap` | 頂点・エッジの反対側 (見つからなければ -1)。`unmatched` = 見つからない頂点の数 |
| [core/mirror.py:78](../core/mirror.py#L78) `_match_scipy` | cKDTree (`workers=-1`) で頂点、エッジは整数の鍵の `searchsorted` (Python のループなし) |
| [core/mirror.py:115](../core/mirror.py#L115) `_match_grid` | scipy が無いとき: 格子を 2 回 (細かいマス → 見つからない頂点だけ許容値のマス) |
| [core/mirror.py:160](../core/mirror.py#L160) `edges` / [:165](../core/mirror.py#L165) `waypoint` / [:173](../core/mirror.py#L173) `with_mirror` | 反対側のエッジ / 端点 / エッジ + 反対側 (重複なし) |
| [core/settings.py:79](../core/settings.py#L79) | 設定 `symmetry` (`-sy`)・`mirrorSpace` (`-ms`)・`mirrorAxis` (`-ma`)。欄「対称」 |
| [scene/mirror.py](../scene/mirror.py) `MirrorPlane` / `mirror_plane` / `maya_symmetry_values` | 対称の面をツールの設定から決める / Maya の対称の設定をツールの設定の値に直す |
| [scene/mirror.py:99](../scene/mirror.py#L99) `cached_mirror_map` | 鍵 (UUID, 空間, 軸, 許容値, トポロジー) で `CACHE_SIZE` (8) 個まで覚える |
| [scene/mesh.py:239](../scene/mesh.py#L239) `localPoints` | オブジェクトの空間の位置 (Transform を動かしても組は同じ) |
| [scene/targets.py:81](../scene/targets.py#L81) `MeshTarget.mirror` | メッシュごとの対応表 |
| [tool/context.py:440](../tool/context.py#L440) `mirrorPlane` / [:444](../tool/context.py#L444) `mirrorFor` | 対称がオフなら None。作ったときは時間と見つからない頂点の数をログに |
| [tool/context.py:469](../tool/context.py#L469) `_prebuild_mirrors` / [:210](../tool/context.py#L210) | ツールに入ったら手すきのときに先に作る (C。対称がオフでも) |
| [tests/UVPathCut/test_mirror.py](../../tests/UVPathCut/test_mirror.py) | 格子の版: 総当たりと一致・ほかの軸・見つからない頂点とエッジ・中心のエッジ・`with_mirror` |
| [tests/UVPathCut/mayapy/test_mirror.py](../../tests/UVPathCut/mayapy/test_mirror.py) | scipy の版 = 格子の版 (3 軸・ずらしたメッシュ)・面の決め方・オブジェクト / ワールド・使い回し A / B と上限・先に作る・時間 |

## 仕組み

### 反対側の探し方

```
頂点 v の位置 p -> 面で鏡映 q (軸の成分の符号を反対に)
  -> q から許容値以内で最も近い頂点 = 反対側 (無ければ -1。面の上の頂点は自分)
エッジ (a, b) -> (反対側 a', 反対側 b') を結ぶエッジ (無ければ -1)
```

scipy の版は、エッジの反対側を「(小さい番号, 大きい番号) を 1 つの整数にした鍵」で探す。元のエッジの鍵を
並べておき、反対側の組の鍵を `searchsorted` で一度に探す。辞書を作って 1 本ずつ引くと 9 万エッジで 60 ms
かかっていた (全体 110 ms -> 55 ms)。

### 使い回し

| | 何を | どうやって |
|---|---|---|
| A | トポロジーが同じ間は作り直さない | 鍵に位置を入れない (ポーズで左右がずれても組が残る) |
| B | ツールを出入りしても覚える | モジュールに 8 個まで (メッシュの UUID なので名前を変えても同じ) |
| C | ツールに入った直後に先に作る | `maya.utils.executeDeferred(_prebuild_mirrors)` |

### 速さ (4.5 万頂点の球)

| | 2027 | 2022 |
|---|---|---|
| scipy | 55 ms | 70 ms |
| Python (格子) | 404 ms | 518 ms |

## 落とし穴

- 同じ距離の頂点が 2 つあると、scipy の版と格子の版で選ぶものが違いうる (テストのメッシュでは起きない)
- ワールドの空間で Transform を面から離すと、全部の頂点の反対側が見つからない (オブジェクトの空間なら同じ)
- mayapy では `executeDeferred` の時期が GUI と違うので、テストは `_prebuild_mirrors` を直接呼ぶ

## 試し方 (17a。まだ操作には効かない)

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polySphere(name="ball"); cmds.select("ball")
import UVPathCut; UVPathCut.tool()
# スクリプトエディタに「対応表 |ball|ballShape MirrorPlane(object X ...) N ms (scipy) (先に作成)」
# ツール設定のウィンドウに「対称」の欄 (対称・空間・軸)
```


## 17b: パスのモード

### 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/session.py:76](../core/session.py#L76) `PathSegment.setMirror` / [:94](../core/session.py#L94) `allEdges` | 区間が反対側のエッジ (`mirror_edges`) と見つからない数を持つ。`allEdges` は両側 |
| [scene/edit.py:264](../scene/edit.py#L264) `confirm_path(mirror=)` | 確定のときに反対側を決める。選択・自動カットは `allEdges` なので両側。Undo の名前に「両側」 |
| [core/draw_list.py:48](../core/draw_list.py#L48) `ROLE_MIRROR` / [:75](../core/draw_list.py#L75) / [:206](../core/draw_list.py#L206) `mirror_items` | 反対側はプレビューの色をうすく (不透明度 0.45)。色の設定「プレビュー」に従う |
| [tool/manipulator.py:116](../tool/manipulator.py#L116) `setMirrorProvider` / [:129](../tool/manipulator.py#L129) `_update_mirror_items` / [:343](../tool/manipulator.py#L343) | プレビュー・スタート・拾ったものの反対側。プレビューが変わったときだけ作る |
| [tool/context.py:300](../tool/context.py#L300) / [:306](../tool/context.py#L306) | 確定に対応表を渡す / 反対側が見つからないエッジを警告 |
| [tool/context.py:607](../tool/context.py#L607) | 対称・空間・軸を変えたら反対側の表示を作り直す |
| [tests/UVPathCut/mayapy/test_edit.py:388](../../tests/UVPathCut/mayapy/test_edit.py#L388) | 選択・自動カット・まとめての縫合が両側、Undo / Redo で同じ反対側 |
| [tests/UVPathCut/mayapy/test_context.py:338](../../tests/UVPathCut/mayapy/test_context.py#L338) | 対称で確定した区間は、あとでオフにしても両側のまま |
| [tests/UVPathCut/test_session.py](../../tests/UVPathCut/test_session.py) / [test_draw_list.py](../../tests/UVPathCut/test_draw_list.py) | 反対側の決め方 (面の上のエッジは足さない) / 描く一覧と色 |

### 仕組み

```
クリック (確定)
  -> mirrorFor(target)              対称がオンなら対応表 (覚えておいたもの)
  -> confirm_path(..., mirror)
       segment.setMirror(mirror)    反対側のエッジを区間が持つ (確定したときに決める)
       選択 / 自動カット             segment.allEdges() = 自分 + 反対側
  まとめてカット・クリア・描画も allEdges を使うので、そのまま両側になる
```

- **確定したときに決める**: 反対側は区間が持つので、あとで対称をオフにしたり、Maya の対称の設定を変えたりしても、
  確定した区間は確定したときのまま (Undo / Redo でも同じ)
- **反対側の表示**: スタート・プレビュー・マウスの下のものの反対側を、うすい色で描く。描くたびに対応表を引かないよう、
  プレビューが変わったとき (拾ったものが変わった・スタートが変わった・設定が変わった) に一覧を作っておく

### 試し方 (17b。ボタンと X キーは 17d)

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polySphere(name="ball"); cmds.select("ball")
import UVPathCut; UVPathCut.tool()
cmds.uvPathCutCtx("uvPathCutContext", e=True, symmetry=True)   # かツール設定の「対称」
```

| # | 操作 | 期待 |
|---|---|---|
| 1 | X が 0 でない所にスタート、マウスを動かす | 反対側にうすいスタートとプレビュー、マウスの下の反対側 |
| 2 | 確定 | 両側の区間が描かれ、両側のエッジが選ばれる。Undo の名前に「両側」 |
| 3 | 自動カット / C | 両側がカットされ、Ctrl+Z 1 回で戻る |
| 4 | 対称をオフにする | 確定済みの区間は両側のまま。新しい確定は片側 |
| 5 | ツール設定で軸を Z にする | 反対側の表示が Z の面で反対になる (Maya の対称の設定には左右されない) |
| 6 | Maya の対称をワールド Z にして「Maya の設定を読み込む」 | 空間・軸・許容値がツール設定に写る |


### 変更: 対称の面はツールの設定だけ (17b の GUI 確認のあと)

| 場所 | 内容 |
|---|---|
| [core/settings.py](../core/settings.py) `mirrorTolerance` | 許容値も設定に (`-mt`、既定 0.1、欄の桁は `Setting.precision` = 4) |
| [scene/mirror.py](../scene/mirror.py) `mirror_plane` | 設定の値だけから面を作る |
| [scene/mirror.py](../scene/mirror.py) `maya_symmetry_values` | Maya の対称 (空間・軸・許容値) をツールの設定の値に。トポロジーの対称なら空間は写さない |
| [core/actions.py](../core/actions.py) `readMayaSymmetry` / `Action.section` | ツール設定の「対称」の欄にだけ出すボタン (ビューのボタン・キーは無い) |
| [core/tool_ui_text.py](../core/tool_ui_text.py) | `Action.section` の操作のボタンを、その欄に置く |
| [tool/context.py](../tool/context.py) `readMayaSymmetry` | 写してログに出す |
| [tests/UVPathCut/mayapy/test_mirror.py](../../tests/UVPathCut/mayapy/test_mirror.py) | Maya の対称がオンでもツールの設定の面・読み込み・コンテキストから読み込む |


## 17c: 選択のモード

対称の設定 (対称・空間・軸・許容値) は 1 組で、パスと選択の両方のモードに効く。

### 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [scene/edit.py:334](../scene/edit.py#L334) `apply_selection(mirrors=)` / [:350](../scene/edit.py#L350) | メッシュごとに、選んだエッジ + 反対側 (`with_mirror`) を実行。覆われた区間も足したエッジで決める |
| [tool/context.py:363](../tool/context.py#L363) | `applySelection` が対称なら対応表を渡す。反対側が見つからないエッジを警告 |
| [tool/context.py:457](../tool/context.py#L457) `selectionMirrorEdges` / [:472](../tool/context.py#L472) `updateSelectionMirror` | 選んだエッジの反対側 (選んでいないもの) と、その描く一覧 |
| [tool/context.py:449](../tool/context.py#L449) | 選択が変わったとき (updateTargets) に作り直す。対称の設定・モードが変わったときも |
| [tool/manipulator.py:151](../tool/manipulator.py#L151) `setSelectionMirror` / [:354](../tool/manipulator.py#L354) | 選択のモードで、選んだエッジの反対側をうすく描く |
| [tool/manipulator.py:146](../tool/manipulator.py#L146) | ホバーのエッジとループの反対側も描く |
| [tests/UVPathCut/mayapy/test_edit.py:424](../../tests/UVPathCut/mayapy/test_edit.py#L424) | 片側を選んで両側をカット・覆われた区間 (両側を持つもの) に印・Undo・対応表なしは片側 |
| [tests/UVPathCut/mayapy/test_context.py:363](../../tests/UVPathCut/mayapy/test_context.py#L363) | 選択のモードの対称: 反対側の一覧・両側のカット・オフで消える |

### 仕組み

```
選択が変わる -> SelectionChanged -> (手すきのとき) updateTargets -> updateSelectionMirror
  選んだエッジ (メッシュごと) -> 対応表で反対側 -> 選んでいないものをうすく描く
C (選択のモード・対称)
  -> applySelection -> mirrorFor(メッシュ) -> apply_selection(..., mirrors)
       選んだエッジ + 反対側 を polyMapCut (メッシュごと)、覆われた区間に印、選択は前のまま
```

- 選択は変えない (反対側を選び足さない)。カット / 縫合するときに足し、何が足されるかは、うすい色で見せる
- ボタンの数 (「カット N」) は選んだエッジの数のまま (反対側は含まない)。描くたびに対応表を引かないため。
  実行した本数はログに出る

### GUI での確認表 (17c)

| # | 操作 | 期待 |
|---|---|---|
| 1 | 対称オン・選択のモードでエッジを選ぶ | 反対側にうすい線 (選択は片側のまま) |
| 2 | マウスを乗せる (ループのプレビューもオンにして) | ホバーのエッジ・ループの反対側もうすく出る |
| 3 | C | 両側がカットされ、ログの本数が両側の合計。Ctrl+Z 1 回で戻る |
| 4 | 対称をオフにする | 反対側の線が消え、C は片側だけ |
| 5 | パスで (対称オン・自動 OFF) 確定した区間を、選択のモードで片側だけ選んで C | 区間がカット済みの色になる |


### 変更: 両方のモードで Maya の対称を優先 (17c の GUI 確認のあと)

| 場所 | 内容 |
|---|---|
| [scene/mirror.py](../scene/mirror.py) `maya_plane` / `mirror_plane` / `plane_text` | Maya の対称が効いていればその面。無ければツールの設定 |
| [tool/context.py](../tool/context.py) `symmetryActive` | ツールの対称がオンか、Maya の対称がオン。`mirrorFor` / `selectionMirrorEdges` はこれで判断 |
| [tool/context.py](../tool/context.py) `checkMayaSymmetry` | Maya の対称の変更には通知が無いので、`syncMesh` (マウスの移動) で 0.5 秒に 1 回まで見て、変わったら表示・ウィンドウを合わせる |
| [tool/tool_ui.py](../tool/tool_ui.py) `maya_symmetry_text` / [core/tool_ui_text.py](../core/tool_ui_text.py) `MAYA_SYMMETRY_KEYS` | ウィンドウの対称の欄: Maya の面の説明と、空間・軸・許容値を灰色に |
| テスト | [mayapy/test_mirror.py](../../tests/UVPathCut/mayapy/test_mirror.py) (Maya 優先・トポロジーはツール・ツールの対称がオフでも効く・変更の検出) / [mayapy/test_tool_ui.py](../../tests/UVPathCut/mayapy/test_tool_ui.py) / [test_tool_ui_text.py](../../tests/UVPathCut/test_tool_ui_text.py) |

| # | 操作 | 期待 |
|---|---|---|
| 7 | Maya の対称をワールド Z にする (ツールの対称はオフ・軸 X のまま) | ツール設定の空間・軸・許容値が灰色、「Maya の対称: ワールド Z  許容値 0.1」。マウスを動かすと反対側が Z で出る |
| 8 | 選択のモードで片側を選んで C | Z の両側だけがカットされる (X の反対側は足されない) |
| 9 | Maya の対称をオフにする | 灰色が戻り、ツールの対称 (オフなら片側) |


### 変更: 選択のモードでは表のエッジだけを選ぶ (17c の GUI 確認のあと)

**症状**: 選択のモードで、プレビューしたループと違う場所 (1〜2 段ずれたリング) が選ばれることがあった。

**調べ方**: デバッグ表示 (`UVPathCut.log.set_debug(True)`) で、選択が変わるたびに「ホバーで拾っていたエッジ・
プレビューのループ・実際に選ばれたエッジ・Maya の対称」を出した ([tool/context.py](../tool/context.py) `_debug_selection`)。

```
ホバー |pSphere1|pSphereShape1 e[215]  ループ 20 本 [200, 201, ...]
選択 |pSphere1|pSphereShape1 1 本 [162]
Maya の対称 (False, ...)
```

Maya の対称はオフ。ホバーはリング 200〜219 の 16 番目、選ばれたのはリング 160〜179 の 3 番目で、
球のほぼ反対側 = **Maya が隠れた裏側のエッジを拾っていた**。このツールのホバーは表の面だけを拾うが、
Maya の選択は「カメラベースの選択」(`selectPref -useDepth`。既定オフ) がオフだと裏側も拾う。
裏側のエッジが画面でマウスに近く重なったときだけ起きる (「何回か」)。

**対応 (ユーザーの判断: 案 A)**: 選択のモードの間だけカメラベースの選択をオンにし、パスに戻す・ツールを抜ける・
設定をオフにすると元に戻す。

| 場所 | 内容 |
|---|---|
| [scene/select_pref.py](../scene/select_pref.py) `DepthOverride` | `apply` (元の値を optionVar `uvPathCutSavedUseDepth` に書いてオン) / `restore` / `recover` |
| [core/settings.py](../core/settings.py) `frontOnly` | 設定「表だけ選ぶ」(既定オン、`-fo`、欄「モード」) |
| [tool/context.py](../tool/context.py) `_update_depth` / `_restore_depth` | モード・設定が変わったとき、ツールに入ったとき・抜けたとき |
| [tool/context.py](../tool/context.py) `toolOnSetup` | 前に戻せなかった値 (Maya が落ちたなど) があれば先に戻す |
| [log.py](../log.py) `set_debug` / `debug` | 調べるときだけ出すログ |
| [tests/UVPathCut/mayapy/test_context.py](../../tests/UVPathCut/mayapy/test_context.py) | モードの出入り・設定のオフ・もともとオンのまま・落ちたあとの recover |

| # | 操作 | 期待 |
|---|---|---|
| 10 | 選択のモードに入る | 「カメラベースの選択をオンにします」。プリファレンスの「カメラベースの選択」がオン |
| 11 | 球の上でダブルクリックを繰り返す | いつもプレビューと同じループが選ばれる |
| 12 | Tab でパスに戻す / 別のツールにする | 「元に戻しました」。プリファレンスが元の値 |


### 整理 (16d のあと)

選択をツールで行うようにしたので、次のものを外した。

| 外したもの | 理由 |
|---|---|
| 「Maya の設定を読み込む」(readMayaSymmetry・`maya_symmetry_values`・`Action.section`) | Maya 優先にしたので、Maya の対称がオンならそのまま使われる |
| `scene/select_pref.py` (カメラベースの選択の切り替えと、前の版の後始末) | ツールで選ぶので Maya の設定に触れない。後始末はツールを有効にしたときに済んでいる |
| デバッグ表示 (`_debug_selection`・`log.debug`) | 原因が分かったので |


## 17d: ボタンとキー

| 場所 | 内容 |
|---|---|
| [core/actions.py](../core/actions.py) `symmetry` / `_symmetry_label` | 操作「対称」(設定 symmetry の切り替え・**X** キー・両方のモードのボタン)。表示は「対称 OFF」「対称 X」、Maya の対称が効いていれば「Maya 対称 Z」 |
| [core/actions.py](../core/actions.py) `ActionState.maya_axis` | Maya の対称の軸 (ボタンの表示用) |
| [tool/context.py](../tool/context.py) `actionState` | 覚えている Maya の対称の設定 (`_maya_symmetry`。ツールを有効にしたときと checkMayaSymmetry で更新) から軸を渡す (描くたびに Maya に問い合わせない) |
| [tool/context.py](../tool/context.py) `runAction` | Maya の対称がオンのときに切り替えたら「切り替えても両側に効きます」と警告 |
| テスト | [test_actions.py](../../tests/UVPathCut/test_actions.py) `test_symmetry_label`・ボタンの並び / [mayapy/test_context.py](../../tests/UVPathCut/mayapy/test_context.py) `case_symmetry_button_and_key` |

ヘルプライン・ツール設定の「キーとマウス」は操作の表から作るので、「X 対称」が自動で入る。
X は Maya の標準では「押している間、グリッドにスナップ」(このツールは移動しないので影響しない)。

ボタンが 8 つ (パスのモード) になったので、幅 760 ピクセルより狭いビューでは 2 段になる。

| # | 操作 | 期待 |
|---|---|---|
| 1 | パス・選択のどちらのモードでも | ボタンに「対称 OFF」 |
| 2 | X / ボタン | 「対称 X」(軸はツール設定) になり、両側に効く。もう一度で OFF |
| 3 | Maya の対称をワールド Z にしてマウスを動かす | ボタンが「Maya 対称 Z」 |
| 4 | その状態で X | 警告が出て、両側に効いたまま |
