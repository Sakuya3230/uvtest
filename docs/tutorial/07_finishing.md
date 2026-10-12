# 7. 仕上げと全体のコツ (手順 22)

[目次](README.md) ・ 前: [6. モードを足す](06_modes.md)

## 手順 22: 扱えないメッシュ・分割・資料

**扱えないメッシュ** (mayapy で試して決める)

| メッシュ | polyMapCut | 対応 |
|---|---|---|
| シェイプがロック (lockNode) | 失敗。MDGModifier からは「Unexpected Internal Failure」としか分からない | 前もって調べ、そのメッシュは実行せず理由を警告 |
| Transform だけロック / リファレンス | 成功 | 何もしない |
| インスタンス | 成功 (ほかのインスタンスも変わる) | 対象にしたときに知らせる |
| UV が無い | エラーにならないが変わらない | 警告 |

シーンを変える関数の思わぬ失敗は、トレースバックではなく警告にする (コマンドは失敗したら変更を戻して Undo にも積まない)。

**分割**: コンテキストが大きくなったら役割ごとにミックスインに分ける
(`UVPathCutContext(SelectingMixin, RingMixin, SymmetryMixin, MPxSelectionContext)`)。プラグインが引く名前は
元のモジュールから再び公開する。リロードの順は「部品 -> 本体」。

**資料**: 使う人向け (USAGE) と、作り方の記録 (段階ごと) を分ける。

**実装**: [scene/mesh.py](../../scene/mesh.py) `edit_blocker` / `mesh_notes`・[tool/context.py](../../tool/context.py) `_run_edit` / 記録 [18_finishing.md](../18_finishing.md)

## テストの組み立て

| | 何を | どこで | 例 |
|---|---|---|---|
| core | 計算・表・文字列 (MEL) | pytest (Python 3.7 でも動く書き方に) | 最短パス・断面・対応表 (Python の版)・操作の表 |
| scene | シーンを読む / 変える・Undo | mayapy (`maya.standalone`。版ごとに) | 確定と Undo・カットのノード・選択 |
| tool | コンテキストの流れ | mayapy で、コンテキストを直接作り、GUI が要る所 (マニピュレータ・キーの取り付け・描き直し) を差し替える | クリック・選択・輪切り (視線と投影の関数を渡す) |
| Qt | キー・ダブルクリック・ホイール | mayapy (Qt のアプリケーションはある)。イベントを作ってフィルターに直接渡す | QKeyEvent / QMouseEvent / QWheelEvent |
| GUI | 描画・マウスの実際の動き | 段階ごとの確認表 | 見た目・追従・ダブルクリック |

- numpy / scipy の版と Python の版は、**同じ結果になることを mayapy で比べる** (pytest の Python では numpy が使えない環境もある)
- 依存の向き (`tool -> scene -> core`、core は maya / Qt を import しない) を AST で検査するテストを置く
- mayapy ではコンテキストのコマンドがコンテキストを作らない (`cmds.uvPathCutCtx` が False を返す)。
  `setAllowDoubleClickAction` のような「実体が要るもの」は GUI でしか確かめられない
- GUI で原因が分からないときは、調べる用の関数 (例: 今のビューで計算の各段階の数を出す) を一時的に足す

## 落とし穴の一覧

| 分類 | 落とし穴 | 対処 |
|---|---|---|
| リロード | creator がクラスを直接持つと古いクラスが作られる | creator が毎回 `importlib` で引く |
| リロード | `super(クラス, self)` がリロード後に TypeError | 引数なしの `super()` |
| メッシュ | カットのあとに古い MFnMesh を使うと Maya が落ちる | dirty の通知で捨て、使うときに作り直す |
| メッシュ | `MItMesh*` は渡したパスの参照を保持しない | パスを変数で持っておく |
| Undo | Python の cmds で呼ぶとコマンドの Undo の名前が空 | MEL で `-n "名前"` |
| Undo | `setActiveSelectionList` は Undo に載らない | 前の選択を覚えて戻す変更にする |
| Undo | polyMapCut が選択を変える | 選択の変更をいつも最後に |
| Undo | ハイライトの付け直しが Undo に積まれ、Ctrl+Z がずれる | `undoInfo(stateWithoutFlush=False)` で囲む |
| コンテキスト | 基底の `toolOnSetup` を呼ぶと SystemError | 呼ばない |
| コンテキスト | 問い合わせで文字列を返すと kFailure | 番号で返す |
| マウス | `MPxContext` に移動のイベントが無い | マニピュレータの `registerForMouseMove` / `doMove` |
| マウス | 2 回目の押下 (ダブルクリック) がコンテキストに届かない | Qt の `MouseButtonDblClick` |
| 描画 | ツールのドラッグ中、マニピュレータが描き直されない | `doDrag` の drawMgr に描く |
| 描画 | 2D の描画は押せる部品にならない | 画面の矩形を 3D の平面に戻して `kSelectable` |
| 選択 | Maya の選択は Maya の対称・裏側を拾う | 選択のモードはツールが選ぶ |
| キー | Maya のホットキーに取られる | ShortcutOverride を accept |
| ウィンドウ | `Properties` は最初の 1 回しか呼ばれない | `Values` で消して呼び直す |
| 最短パス | `polySelect -shortestEdgePath` は長さの最短でない | 自分の Dijkstra で答え合わせ |
| 対称 | Maya の対称の変更に通知が無い | 0.5 秒に 1 回まで見る |
| 速さ | ドラッグのたびに Maya に問い合わせると遅い | 押したときに用意し、ドラッグ中は numpy の配列の計算だけ |
