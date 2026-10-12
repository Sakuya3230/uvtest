# 段階 16: 選択のモード

[目次](README.md) ・ 前: [段階 15](15_straightness.md) ・ 次: [段階 17](17_symmetry.md)

段階 16 は 3 つに分けて進める。

| | 内容 | 状態 |
|---|---|---|
| 16a | モードの設定と切り替え (Tab)・E / V・クリックの振り分け・ダブルクリックの選択 | 実装済み |
| 16b | 選んだエッジのカット / 縫合 (全メッシュで 1 回の Undo・覆われた区間の印) | 実装済み |
| 16c | ホバーでループのプレビュー | 実装済み |
| 16d | 選択をツールで行う (作り直し。段階 17c の確認のあと) | 実装済み |

## 決めた仕様

- ツールに「パス」と「選択」の 2 つのモード。切り替えは **Tab**・ビューのボタン・ツール設定のウィンドウ
- 拾うもの (頂点 / エッジ) は **E = エッジ・V = 頂点** (切り替えではなく、その値にする)。
  選択のモードでも設定は変える (パスのモードに戻ったときに効く)
- 選択のモードは **エッジだけ**。クリック・ドラッグ・Shift / Ctrl・**ダブルクリックのループ** は Maya の選択のまま
- 選択のモードでは自動カットは無い (ボタン・キーで実行)
- 確定した区間とスタートは、モードを替えても残す

## 16a: 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/settings.py:63](../core/settings.py#L63) `mode` | 設定「モード」(CHOICE: path / select。`-md`、欄「モード」)。フラグ・ウィンドウ・保存は表から自動 |
| [core/actions.py:114](../core/actions.py#L114) `mode` | Tab でモードを切り替える操作 (ボタンにもなる) |
| [core/actions.py:120](../core/actions.py#L120) `pickEdge` / `pickVertex` | E / V。`value` で設定をその値にし、`button=False` でボタンにしない |
| [core/actions.py:101](../core/actions.py#L101) `shownIn` / [:160](../core/actions.py#L160) `visible_actions` | `modes` で、ボタンを出すモードを決める (拾うもの・自動・自動の操作はパスのモードだけ) |
| [core/actions.py:155](../core/actions.py#L155) `action_index` | ボタンのハンドルの名前は表の番号のまま (見えるボタンが変わっても、押したボタンの見分けは変わらない) |
| [core/panel.py](../core/panel.py) `panel_layout(actions=None)` | 見えるボタンだけを並べる (省くとパスのモードのボタン) |
| [tool/drawing.py:200](../tool/drawing.py#L200) | ボタンのハンドルを `action_index` で決める |
| [tool/manipulator.py:150](../tool/manipulator.py#L150) `setMode` / [:159](../tool/manipulator.py#L159) `_visible` / [:194](../tool/manipulator.py#L194) | 選択のモードでは頂点 / エッジを拾わない・スタートとプレビューを描かない・そのモードのボタンだけ |
| [tool/context.py:148](../tool/context.py#L148) `_enable_double_click` | `setAllowDoubleClickAction` (コンストラクタで失敗しても続け、`toolOnSetup` で試し直す) |
| [tool/context.py:233](../tool/context.py#L233) `_wants_click` | 選択のモードではいつも False (クリックを基底の選択に任せる) |
| [tool/context.py:358](../tool/context.py#L358) `runAction` | `value` の操作は設定をその値にする |
| [tool/context.py:469](../tool/context.py#L469) `_enter_mode` / [:483](../tool/context.py#L483) `_ensure_edge_mode` | モードを替えたら、ヘルプライン・マニピュレータを替え、選択のモードなら対象をエッジのハイライトに戻す (Undo に積まない) |
| [tool/context.py:478](../tool/context.py#L478) `_redraw` | ビューの描き直しを 1 か所に (テストで差し替える) |
| [tests/UVPathCut/test_actions.py](../../tests/UVPathCut/test_actions.py) | モードごとのボタン・値にする操作・キーの表 (Tab / E / V) |
| [tests/UVPathCut/mayapy/test_context.py:199](../../tests/UVPathCut/mayapy/test_context.py#L199) 〜 | ダブルクリックの有効化が止まらない・クリックの振り分け・E / V・ハイライトと Undo・区間とスタートが残る |
| [tests/UVPathCut/mayapy/test_keys.py](../../tests/UVPathCut/mayapy/test_keys.py) | E / V を受け取り、Shift+E は Maya に渡す |

## 仕組み

### クリックの振り分け

```
doPress
  _wants_click ?   パスのモード かつ 修飾キーなしの左クリック かつ メッシュの上で拾えている
    はい   -> ツールが受け取る (基底を呼ばない = 選択は変わらない)。離したときにスタート / 確定
    いいえ -> 基底 (MPxSelectionContext) の doPress / doDrag / doRelease = Maya の普通の選択
              ダブルクリックのループも、基底に任せた操作でだけ効く
```

選択のモードでは `_wants_click` がいつも False なので、すべての操作が Maya の選択になる。
ダブルクリックのスマートな選択 (エッジのループ) は、`setAllowDoubleClickAction()` で有効にする
(通常の選択ツールと同じ。ウェイトスライダーで確認済み)。

### 操作の表の拡張

```
Action("mode",       setting="mode", key=Tab)                     切り替え (ボタン)
Action("pick",       setting="pickMode", modes=("path",))          切り替え (パスのモードだけボタン)
Action("pickEdge",   setting="pickMode", value="edge", key=E, button=False)   その値にする (キーだけ)
Action("pickVertex", setting="pickMode", value="vertex", key=V, button=False)
```

ボタン・キー・ツール設定のウィンドウ・ヘルプラインは、どれもこの表から作るので、表の 3 行と設定の 1 行で
モードの切り替えがすべての入り口にそろう。

## 落とし穴

- **mayapy ではコンテキストのコマンドがコンテキストを作らない** (`cmds.uvPathCutCtx("名前")` が False を
  返し、`makeObj` が呼ばれない)。`setAllowDoubleClickAction` が通るかは GUI でしか確かめられない。
  mayapy のテストは、失敗してもツールが止まらないことだけを確かめる
- ボタンのハンドルの名前を「並べた順」にすると、モードで見えるボタンが変わったときに、押したボタンが
  別の操作になる。表の番号 (`action_index`) にする
- E を受け取らずに Maya に渡すと、回転ツールに切り替わってツールを抜けてしまう。選択のモードでも受け取る
- ハイライトを付け直す処理を Undo に積むと、Ctrl+Z がハイライトを戻すだけになる。`undoInfo(stateWithoutFlush=False)` で外す

## GUI での確認表 (16a)

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polySphere(name="ball"); cmds.select("ball")
import UVPathCut; UVPathCut.tool()
```

| # | 操作 | 期待 |
|---|---|---|
| 1 | ビューの下のボタン | 左端に「パス」。拾うもの・自動・自動の操作・カット・縫合・クリアが並ぶ |
| 2 | Tab | ボタンが「選択」になり、拾うもの・自動・自動の操作が消える。ヘルプラインが選択の説明に |
| 3 | 選択のモードでエッジをクリック・Shift クリック・矩形 | Maya の普通の選択 |
| 4 | 選択のモードでエッジをダブルクリック | エッジのループが選ばれる (スクリプトエディタに警告が出ていない) |
| 5 | 選択のモードでマウスを動かす | 頂点 / エッジの強調・パスのプレビューは出ない。確定した区間は見える |
| 6 | 選択のモードで E / V を押す | ツールのまま (回転ツールにならない)。Tab でパスに戻ると、拾うものが変わっている |
| 7 | パスのモードで E / V | 拾うものがエッジ / 頂点になる (押し直しても変わらない) |
| 8 | パスでスタートを置く → Tab → Tab | スタートが残っていて、続けて確定できる |
| 9 | ツール設定のウィンドウ | 「モード」の欄があり、ボタン・Tab と連動する |
| 10 | パスのモードでメッシュの上をダブルクリック | ループは選ばれない (クリックはパスの操作) |


## 16b: 選んだエッジのカット / 縫合

C / S・ビューのボタン・ツール設定のボタン・`-apply` は、どれも `applyOperation` を通り、モードで振り分ける。

| モード | 対象 | ボタンの数 |
|---|---|---|
| パス | ためた (未実行の) 区間 (今までどおり) | ためた区間の数 |
| 選択 | 選んでいる、対象のメッシュのエッジ | 選んだエッジの数 |

### 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/actions.py:113](../core/actions.py#L113) `_apply_count` / [:141](../core/actions.py#L141) | ボタンの数と押せるかをモードで替える。メソッドは `applyOperation` |
| [scene/targets.py:172](../scene/targets.py#L172) `selectedEdges` | 選んでいる対象のメッシュのエッジ (メッシュごと・対象の順)。エッジ以外は使わず `ignored` |
| [scene/edit.py:317](../scene/edit.py#L317) `covered_segments` | 未実行の区間のうち、エッジがすべて選ばれているもの |
| [scene/edit.py:329](../scene/edit.py#L329) `apply_selection` | メッシュごとの UVChange + 覆われた区間の印 + 選択を戻す、を 1 回の Undo |
| [tool/context.py:325](../tool/context.py#L325) `applyOperation` / [:331](../tool/context.py#L331) `applySelection` | モードで振り分ける / 選択のカット / 縫合とログ |
| [tool/context.py:377](../tool/context.py#L377) | 選択のモードのときだけ、選んだエッジを数える (ボタンの数) |
| [tool/context.py:631](../tool/context.py#L631) | `-apply` もモードに従う |
| [tests/UVPathCut/mayapy/test_edit.py:343](../../tests/UVPathCut/mayapy/test_edit.py#L343) | 2 メッシュ・1 回の Undo / Redo・覆われた区間だけ印・選択が戻る |
| [tests/UVPathCut/mayapy/test_targets.py:110](../../tests/UVPathCut/mayapy/test_targets.py#L110) | 対象の順・対象外のメッシュ・頂点 / 面 / オブジェクトを除く・シェイプの名前 |
| [tests/UVPathCut/mayapy/test_context.py:292](../../tests/UVPathCut/mayapy/test_context.py#L292) | C / S がモードで対象を替える・ボタンの数 |

### 仕組み

```
C (選択のモード)
  -> applyOperation("cut") -> applySelection
  -> targets.selectedEdges()       MSelectionList を 1 項目ずつ。エッジのコンポーネントで、対象のメッシュのものだけ
  -> apply_selection([(シェイプ, エッジ, セッション)], "cut")
       メッシュごとに UVChange (polyMapCut)
       セッションがあれば covered_segments -> OperationChange (カット済みの印)
       SelectionChange(前, 前)       polyMapCut が選び直すので、最後に元へ
     -> run_changes (1 回の Undo。変えたセッションに Undo / Redo を知らせる)
```

- **覆われた区間の印**: 選んだエッジでカットしたら、そのエッジだけでできている未実行の区間は、もう実行したのと
  同じ。印を付けないと「未実行」の色のまま残り、パスのモードの C でもう一度カットされる。
  一部だけ選ばれた区間には付けない (残りのエッジはまだ実行していない)
- 印を付けた区間が無くても、対象のメッシュのセッションには Undo / Redo を知らせる (表示を直すため)

### 落とし穴

- `MSelectionList.getComponent` は、オブジェクトだけを選んでいると空のコンポーネント (`isNull`) を返す。
  ノード (DAG でないもの) では例外になる
- Transform の名前でエッジを選んでいても、パスは Transform のことがある。`extendToShape` してから対象と比べる

### GUI での確認表 (16b)

| # | 操作 | 期待 |
|---|---|---|
| 1 | 選択のモードでループをダブルクリック | ボタンが「カット N」「縫合 N」(N = 選んだエッジの数) になり押せる |
| 2 | C | UV がカットされ、選択はそのまま。ログに「選んだエッジ N 本をカットしました」 |
| 3 | Ctrl+Z | カットが 1 回で戻る |
| 4 | 2 つのメッシュでループを選んで S | 両方が縫合され、Ctrl+Z 1 回で両方戻る |
| 5 | パスで区間を確定 (未実行) → Tab → その区間を含むループを選んで C | 区間の色が「カット」になり、Tab でパスに戻ると C のボタンの数が減っている |
| 6 | 頂点や面も混ぜて選んで C | エッジだけがカットされ、警告「エッジ以外の選択は使いません」 |
| 7 | 何も選ばずに C | 何も起きない (ボタンも押せない) |


## 16c: ホバーでループのプレビュー

**設定「ループ」(loopPreview。既定はオフ) がオンのとき**、選択のモードでマウスを動かすと、マウスの下のエッジから、
**ダブルクリックで選ばれるループ** をプレビューの色
(設定「プレビュー」。パスのプレビューと同じ色) で描き、「ループ N 本」と出す。拾うもの (E / V) によらず、
選択のモードではいつもエッジを拾う。

### 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [scene/mesh.py:140](../scene/mesh.py#L140) `edge_loop` | `polySelect -edgeLoopOrBorder <エッジ> -noSelection` (選択を変えない) |
| [scene/mesh.py:239](../scene/mesh.py#L239) `edgeLoop` / [:246](../scene/mesh.py#L246) `edgeSegments` | ループを覚えておく (トポロジーが変わったら捨てる [:234](../scene/mesh.py#L234)) / 描くための両端の位置 |
| [core/draw_list.py:189](../core/draw_list.py#L189) `loop_items` | ループ (ROLE_PATH) + 面 + 拾ったエッジ + 「ループ N 本」 |
| [core/settings.py](../core/settings.py) `pathColor` | 表示名を「プレビュー」に (パスとループで共通) |
| [tool/manipulator.py:166](../tool/manipulator.py#L166) `_pick_kind` | 選択のモードはいつもエッジを拾う |
| [tool/manipulator.py:151](../tool/manipulator.py#L151) `_update_loop` / [:306](../tool/manipulator.py#L306) | 拾ったエッジが変わったときだけループを求め直す / 描く |
| [tests/UVPathCut/mayapy/test_mesh.py:256](../../tests/UVPathCut/mayapy/test_mesh.py#L256) | 球・平面 (境界)・三角形の混ざる立方体で、ダブルクリックと同じ選び方の MEL の結果と一致・選択を変えない |
| [tests/UVPathCut/mayapy/test_mesh.py:281](../../tests/UVPathCut/mayapy/test_mesh.py#L281) | 覚えておく・両端の位置・トポロジーが変わったら求め直す |
| [tests/UVPathCut/test_draw_list.py](../../tests/UVPathCut/test_draw_list.py) `test_loop_items` | 描く一覧 |

### 仕組み

Maya のエッジのダブルクリックは、MEL の `polySelectEdgesEveryN "edgeLoopOrBorder" 1` と同じ選び方
(境界のエッジなら境界の一周、それ以外ならエッジのループ)。これは `polySelect -edgeLoopOrBorder` を呼んでいるので、
同じフラグに `-noSelection` を付ければ、選択を変えずにエッジの番号だけが返る (4.5 万頂点で 2 ms ほど)。

```
doMove -> _update_pick (選択のモードはエッジを拾う)
  拾ったエッジが変わったら updatePreview -> _update_loop
    model.edgeLoop(edge)       覚えていなければ polySelect -edgeLoopOrBorder -noSelection
    model.edgeSegments(loop)   両端の位置
drawUI -> loop_items(pick, segments)
```

### 落とし穴

- `polySelect -edgeLoop` は、境界のエッジでは 1 本しか返さないことがある (平面の端)。ダブルクリックと同じにするには
  `-edgeLoopOrBorder`
- 閉じたループは、最初のエッジの番号が最後にもう一度入る (重複を除く)

### GUI での確認表 (16c)

| # | 操作 | 期待 |
|---|---|---|
| 1 | 選択のモードで球のエッジにマウスを乗せる | ループが黄色で出て「ループ N 本」 |
| 2 | そのままダブルクリック | 選ばれたループがプレビューと同じ |
| 3 | 平面の端のエッジ | 境界の一周がプレビューされ、ダブルクリックも同じ |
| 4 | 頂点を拾う設定 (V) のまま選択のモード | エッジを拾ってループが出る |
| 5 | 大きいメッシュ (polySphere -sa 300 -sh 150) でマウスを動かす | 引っかからない |
| 6 | Tab でパスに戻す | ループは消え、今までのホバー / パスのプレビュー |

### 追加: ループのプレビューの切り替え (GUI での確認のあと)

単一のエッジを選ぶことも多いので、ループを常に出すのは邪魔 (ユーザーの指摘)。設定にして既定はオフにした。

| 場所 | 内容 |
|---|---|
| [core/settings.py](../core/settings.py) `loopPreview` | BOOL・既定オフ・`-lp`・欄「モード」 |
| [core/actions.py](../core/actions.py) `loop` | **L** キー・選択のモードのボタン「ループ ON / OFF」 |
| [tool/manipulator.py](../tool/manipulator.py) `setLoopPreview` | オフならループを求めず、マウスの下のエッジ 1 本 (クリックで選ばれるもの) だけを強調 |
| [tool/context.py](../tool/context.py) `_on_setting_changed` | 設定が変わったらマニピュレータへ |
| [tests/UVPathCut/mayapy/test_context.py](../../tests/UVPathCut/mayapy/test_context.py) `case_loop_preview_toggle` | 既定オフ・L で切り替え・マニピュレータへ届く |

L は Maya の標準では「押している間、カーブの長さを固定」で、このツールでは使わない。

| # | 操作 | 期待 |
|---|---|---|
| 7 | 選択のモードでエッジにマウスを乗せる (既定) | エッジ 1 本と面だけ |
| 8 | L・ボタン・ツール設定の「ループ」 | ループのプレビューが出る / 消える。3 つが連動する |


## 16d: 選択をツールで行う (作り直し)

### なぜ作り直したか

16a〜c では、選択のモードのクリックを Maya の選択 (MPxSelectionContext の基底) に任せていた。段階 17 で
次の問題が続いた (詳しくは [17_symmetry.md](17_symmetry.md))。

| 起きたこと | 原因 |
|---|---|
| ツールの X と Maya の Z の両方が選ばれた | Maya の選択は Maya の対称で選択を両側にする (API で止められない) |
| プレビューと違うリングが選ばれた | Maya は隠れた裏側のエッジも拾う (カメラベースの選択が既定オフ) |
| Maya の設定を一時的に書き換える仕組みが要った | 上を合わせるため |
| ダブルクリックが効かなくなった | 設定をツールの途中で変えた影響と思われる |

拾う (表の面だけ)・ループ・反対側はツールにそろっているので、選択もツールで行う。**プレビューで拾ったものを
そのまま選ぶ** ので、表示と結果が必ず一致する。Maya の設定には触れない。

### 操作

| 操作 | 動き |
|---|---|
| クリック | 拾ったエッジ (ホバーと同じ) を選ぶ。メッシュの外は選択を外す |
| Shift / Ctrl / Ctrl+Shift | 切り替え / 外す / 足す (Maya と同じ) |
| ダブルクリック | ループ (プレビューと同じ `edgeLoopOrBorder`)。Shift のダブルクリックはループを足す |
| ドラッグ (4 ピクセル以上) | 矩形。一部でも矩形にかかり、表の面に付いているエッジ (全メッシュ) |
| 対称 | 選ぶときに反対側も選ぶ (選択そのものが両側)。スクリプトの選択には Maya の対称はかからない |
| Undo | `cmds.select` なので、普通の選択と同じく 1 回の操作 = 1 回の Undo |

できなくなったもの: Maya の選択の機能 (ペイント選択・投げ縄・ソフト選択)。

### 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/selection.py:30](../core/selection.py#L30) `selection_op` / [:41](../core/selection.py#L41) `loop_op` / [:47](../core/selection.py#L47) `combine` | 修飾キー -> 操作 / ダブルクリックの操作 / 集合での結果 |
| [core/selection.py:61](../core/selection.py#L61) `ClickTracker` | ダブルクリック = 同じエッジを間隔 (Qt の設定) の内に 2 回。3 回目は新しい 1 回目 |
| [core/selection.py:88](../core/selection.py#L88) `marquee_edges` | 矩形の中に中点があるエッジ |
| [scene/selection.py:29](../scene/selection.py#L29) `select_edges` | `cmds.select` (-replace / -toggle / -deselect / -add)。置き換えで空なら選択を外す |
| [scene/selection.py:67](../scene/selection.py#L67) `front_edges` / [:46](../scene/selection.py#L46) `CameraInfo` | 表の面 (法線がカメラの方) に付いているエッジ。平行投影は視線の向きで |
| [tool/drawing.py:67](../tool/drawing.py#L67) `project_points` | 全頂点をまとめて画面へ (numpy で MV x P。最初の数点を worldToView と比べ、違えば 1 点ずつ) |
| [tool/drawing.py:105](../tool/drawing.py#L105) `draw_marquee` | 矩形の枠 (doDrag の drawMgr に点線) |
| [tool/context.py:270](../tool/context.py#L270) `_wants_selection` / [:275](../tool/context.py#L275) `doPress` / [:289](../tool/context.py#L289) `doDrag` / [:303](../tool/context.py#L303) `doRelease` | 選択のモードの左ボタンは基底を呼ばず、離したときにクリックか矩形 |
| [tool/context.py:326](../tool/context.py#L326) `selectClick` / [:348](../tool/context.py#L348) `selectInRect` | クリック (ダブルクリックのループ) / 矩形。対称なら反対側を足す |
| 外したもの | `setAllowDoubleClickAction`・設定「表だけ選ぶ」(frontOnly)・カメラベースの選択の切り替え (`scene/select_pref.py`)・`core.selection.combine` |
| [tests/UVPathCut/test_selection.py](../../tests/UVPathCut/test_selection.py) | 修飾キー・集合・ダブルクリック・矩形 |
| [tests/UVPathCut/mayapy/test_context.py:405](../../tests/UVPathCut/mayapy/test_context.py#L405) 〜 | 修飾キーと Undo・メッシュの外・ダブルクリックのループと Shift・対称で両側・矩形で表だけと足す |

### 落とし穴

- 矩形の表 / 裏は面の向きで決める。隠れているか (別の部分の奥にあるか) までは見ない
  (へこんだ形で、手前の部分の奥にある表向きの面のエッジは選ばれる)
- ダブルクリックは 1 回の Undo (1 回目のクリックの選択は取り消してからループを選ぶ)
- `project_points` の行列の計算は GUI でしか確かめられないので、`worldToView` と比べて違えば 1 点ずつに戻す

### GUI での確認表 (16d)

| # | 操作 | 期待 |
|---|---|---|
| 1 | 選択のモードでエッジをクリック | ホバーで強調していたエッジが選ばれる (裏側が選ばれない) |
| 2 | Shift / Ctrl / Ctrl+Shift のクリック | 切り替え / 外す / 足す |
| 3 | ダブルクリック | プレビューと同じループ (Shift なら足す) |
| 4 | ドラッグ | 点線の枠が出て、離すと枠の中の表のエッジが選ばれる (球の裏側は選ばれない) |
| 5 | 対称オン (か Maya の対称オン) でクリック / ダブルクリック / ドラッグ | 反対側も選ばれる |
| 6 | Ctrl+Z | 選択が 1 操作ずつ戻る |
| 7 | メッシュの外をクリック | 選択が外れる |

### 修正 (16d の GUI 確認のあと)

| 症状 | 原因 | 対応 |
|---|---|---|
| ダブルクリックでループにならない | Maya は 2 回目の押下をコンテキストの doPress に届けない (Qt ではダブルクリックは押下とは別のイベント MouseButtonDblClick) | [tool/keys.py](../tool/keys.py) のフィルターが MouseButtonDblClick を受け取り、[context.onDoubleClick](../tool/context.py) -> `selectLoop`。押下が届く場合 (ClickTracker) と重なっても、同じダブルクリックで 2 回選ばない (`_recent_loop`)。押下の無い離しは何もしない |
| 矩形に半分ほど入れないとエッジが選ばれない | 「中点が入るもの」で判断していた | `marquee_edges` を「一部でもかかるもの」(Maya と同じ) に。[core/selection.py](../core/selection.py) `segment_hits_rect` (Liang-Barsky) |

テスト: [mayapy/test_keys.py](../../tests/UVPathCut/mayapy/test_keys.py) `case_double_click_reaches_handler` (QMouseEvent を直接渡す)、
[mayapy/test_context.py](../../tests/UVPathCut/mayapy/test_context.py) `case_qt_double_click_selects_loop_once`、
[test_selection.py](../../tests/UVPathCut/test_selection.py) `test_marquee_touching_edges`。
| ダブルクリックの Undo が 2 回 (ループ -> クリックしたエッジ) | 1 回目のクリックの選択と、ループの選択が別々に Undo に積まれていた | ループを選ぶ前に、1 回目のクリックの選択を `cmds.undo()` で取り消す ([tool/context.py](../tool/context.py) `_undo_first_click`)。直前の Undo の名前が、そのクリックのものと同じときだけ (ほかの操作が間に入っていたら取り消さない)。名前を確かめるため、選択は MEL の `select` で行う (Python の `cmds.select` は Undo の名前が空) |
