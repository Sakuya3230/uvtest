# 3. パスと編集 (手順 8〜11)

[目次](README.md) ・ 前: [2. メッシュと表示](02_mesh_and_view.md) ・ 次: [4. 操作の入り口](04_controls.md)

## 手順 8: グラフと最短パス

**ゴール**: 頂点 / エッジのあいだの、エッジの長さの和が最小のパス。

**作るもの**: `core/graph.MeshGraph` (頂点の位置・エッジ・長さ・隣接)、`core/path` (`Waypoint`・`PathResult`・`PathTree`)

**方法**

- グラフはワールドの位置で 1 回作る (`MFnMesh.getPoints` + エッジの両端)。UV のカット / 縫合では頂点もエッジも
  変わらないので使い回す
- 端点がエッジのとき: スタートなら両端から同時に (距離 0) 探し始め、ゴールならどちらかの端に着けばよい。
  端のエッジ自体もパスに含める
- **スタートを決めたときに 1 回だけ探し、ホバーのたびは道をたどるだけ** (`PathTree`):
  - scipy があれば `scipy.sparse.csgraph.dijkstra(行列, indices=始点, return_predecessors=True, min_only=True)` で
    スタートから全頂点を 1 回 (4.5 万頂点で数 ms)。ゴールへは前の頂点をたどる
  - 無ければ A* (見積もりはゴールまでの直線距離)。ゴールごとに覚える。内側のループは関数を呼ばずに書く
    (隣接リストに長さを入れる・座標を x / y / z の別のリストに)
- numpy / scipy は `core/accel.scipy_modules()` で取り、無ければ Python の版に戻す (どちらも同じ結果をテストで確かめる)
- 答え合わせに Maya の `polySelect -shortestEdgePath` は使えない (長さの最短ではなく、本数が少ない方に寄る)

**確かめ方**: pytest で格子・つながっていない場合。mayapy で scipy と Python の長さが一致すること・時間。

**実装**: [core/graph.py](../../core/graph.py)・[core/path.py](../../core/path.py)・[core/accel.py](../../core/accel.py) / 記録 [05_graph_and_path.md](../05_graph_and_path.md)

## 手順 9: クリック・スタート・プレビュー

**ゴール**: クリックでスタート、マウスを動かすとスタートからのパスのプレビュー、Esc で取り消す。

**方法**

- コンテキストの `doPress` / `doDrag` / `doRelease` を上書きする。メッシュの上の修飾キーなしの左クリックは、
  **基底を呼ばずに**受け取る (呼ばなければ選択は変わらない)。それ以外は基底 (`omui.MPxSelectionContext.doPress(self, ...)`
  と明示して呼ぶ) に任せて普通の選択
- 決めるのは離したとき (押してから少し動かしても、見えているものを使う)
- `core/session.PathSession`: スタートと区間のスタックを持つ。スタートを替えたら `PathTree` を作り直す
- Esc は `abortAction`

**実装**: [core/session.py](../../core/session.py)・[tool/context.py](../../tool/context.py) / 記録 [07_click_and_session.md](../07_click_and_session.md)

## 手順 10: 確定と Undo

**ゴール**: 2 回目のクリックでパスを確定し、区間を積み、エンドを次のスタートにし、確定した全区間のエッジを選ぶ。
これを **1 回の Undo** にする。

**方法**

- **変更 (Change) のリスト** を 1 つの Undo できるコマンド (`MPxCommand`、`isUndoable` が True) で行う。
  変更は `redo()` / `undo()` を持つ小さなオブジェクト (区間を積む・スタートを替える・選択を替える・UV を変える…)。
  コマンドは `redoIt` で順に、`undoIt` で逆順に。途中で失敗したら行った分を戻してから例外を投げる
- コマンドの引数で Python のオブジェクトは渡せないので、モジュールの変数 (`_PENDING`) に置いてから呼ぶ
- Undo の記録の名前は「実行した MEL の文字列」。**Python の cmds で呼ぶと名前が空**になるので、
  `mel.eval('uvPathCutEdit -n "UV パスの確定 (12 本)"')` のように MEL で呼ぶ
- `MGlobal.setActiveSelectionList` はそれ自身では Undo に載らない。前の選択を覚えて戻す (選択の変更も 1 つの Change)
- 選択の変更は**いつも最後に**行う (redo でも undo でも)。polyMapCut はエッジを選んでいると、対象のエッジを選択に
  してしまうため
- コマンドは表示のことを知らない。セッションのリスナーで、コンテキストが描き直す (Undo / Redo のあとも同じ経路)

**確かめ方**: mayapy で確定 -> Undo -> Redo (スタック・スタート・選択)。ツールを抜けたあとの Undo。

**実装**: [scene/edit.py](../../scene/edit.py) `PathEditCommand` / `run_changes` / `confirm_path` / 記録 [08_confirm_and_undo.md](../08_confirm_and_undo.md)

## 手順 11: カット / 縫合

**ゴール**: 確定と同時に (自動) か、ためた区間をまとめて、UV をカット / 縫合する (1 回の Undo)。

**方法**

- `MDGModifier.commandToExecute('polyMapCut "pSphere1.e[3:8]" ...')` を `doIt` / `undoIt` (UVChange)。
  MEL のコマンドが Undo できれば、modifier の `undoIt` で戻る (ヒストリーの有無とも)
- エッジの名前は範囲にまとめる (`e[3:8]`)。長いコマンドを避ける
- 区間に「実行した操作」の印 (OperationChange)。色を変え、まとめて実行の対象から外す
- 自動なら確定と同じ変更のリストに UVChange を足す。まとめて実行は全メッシュの UVChange を 1 つのリストに

**確かめ方**: mayapy で polyMapCut のノードの `inputComponents` (UV の数は継ぎ目と重なると増えないので、
ノードの対象で確かめる)。Undo でノードが消えること。

**実装**: [scene/edit.py](../../scene/edit.py) `UVChange` / `apply_pending_all` / 記録 [09_cut_and_sew.md](../09_cut_and_sew.md)
