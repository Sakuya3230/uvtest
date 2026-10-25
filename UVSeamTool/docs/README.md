# UVSeamTool 解説

ガイドを描いて (最短パス) シームを決め、UV をカット / 縫合するツール。
UVPathCut を、自分で読んで保守できる形に作り直したもの。**版 1 (最短パスだけ)**。SeamGuide の道具 (ライン・カーブ・
フリーハンド・リング・谷・つなぎ線・付き方) を取り入れる開発は、版 2 の `scripts/UVSeamTool2` で続ける
([27_shortest_only.md](27_shortest_only.md))。

**使い方 (操作・キー・メニュー・設定の一覧): [USAGE.md](USAGE.md)**

名前の付け方・クラスの中の並び順・変数の読み書き: [coding_rules.md](coding_rules.md)

## 段階

| 段階 | ページ | 内容 |
|---|---|---|
| 0 | [00_spec.md](00_spec.md) | 仕様と決めごと (名前・環境・コードのルール・骨組み・ガイドの持ち方・設定・画面・機能の一覧) |
| 1 | [01_core_path.md](01_core_path.md) | UI なしで ガイド -> 最短パス -> カット (`cut_path`) |
| 2a | [02_context.md](02_context.md) | コンテキスト・サブツール・クリックで点を足す・Enter でカット (描画なし) |
| 2b | [02b_preview.md](02b_preview.md) | プレビューの描画 (doPtrMoved・drawFeedback・PathTree の使い回し) |
| 3 | [03_guide_set_undo.md](03_guide_set_undo.md) | ガイドの組・Undo (点ごと)・Enter / 右クリックで確定・cut_guides / sew_guides |
| 4 | [04_view_panel.md](04_view_panel.md) | ビューの上のパネル (作成 / 編集・カット・縫合)・モード = サブツールの入れ替え・丸いボタン |
| 5a | [05a_select_guides.md](05a_select_guides.md) | 編集: ガイドを選ぶ (Shift / Ctrl)・ホバー・Delete で消す・選んだガイドをカット / 縫合 |
| 5b | [05b_move_points.md](05b_move_points.md) | 編集: 点をドラッグで動かす (前後の点の PathTree を使い回す・離したら 1 回の Undo)・ドラッグ中の Esc |
| 5c | [05c_insert_delete_points.md](05c_insert_delete_points.md) | 編集: 線のクリックで点を挿入 (そのままドラッグ)・点を選ぶ・Delete で点を消す |
| 6 | [06_save_guides.md](06_save_guides.md) | ガイドの保存 (シェイプのアトリビュートに JSON・編集のたび・トポロジーが違えば使わずに残す)・一覧と削除 |
| 7a | [07a_settings.md](07a_settings.md) | 設定 (色) の表・JSON のファイルへの保存・`UVSeamTool.settings()` |
| 7b | [07b_tool_settings_window.md](07b_tool_settings_window.md) | ツール設定のウィンドウ (MEL は入り口だけ・色・保存したガイドの一覧と削除・Reset Tool) |
| 8 | [08_keys.md](08_keys.md) | キー (Tab: 作成 / 編集・C: カット・S: 縫合。ビューの上・修飾キーなしのときだけ) |
| 9 | [09_external_changes.md](09_external_changes.md) | 外部の変更の検知 (動かす・変形・トポロジー・削除。手すきのときに 1 回だけ読み直す) |
| 10 | [10_multiple_meshes.md](10_multiple_meshes.md) | 複数のメッシュ (いちばん手前で拾う・作成中は全体で 1 本・ref で指す・またがる操作は 1 回の Undo)・選んだメッシュを足す |
| 11 | [11_front_faces.md](11_front_faces.md) | 表の面だけを拾う (allIntersections を近い順に見て、法線がレイと向き合う最初の面) |
| 12 | [12_unsupported_meshes.md](12_unsupported_meshes.md) | 扱えないメッシュ (ロック: 警告・カットと保存を飛ばす / インスタンス・UV なし: 知らせる) |
| 13 | [13_uv_seam_display.md](13_uv_seam_display.md) | UV の切れ目の見え方 (ガイドは状態を持たず、今の UV から求めて切れ目の部分を赤い線に) |
| 14 | [14_edge_mode.md](14_edge_mode.md) | エッジの選択モード (ツールにしたとき・加えたとき。Undo には積まない) |
| 15 | [15_edit_selection.md](15_edit_selection.md) | 編集のモードの選択をガイドだけに (Maya の選択を使わない・ガイドの矩形選択・選んでいれば矩形は点) |
| 16a | [16a_fixed_and_closed.md](16a_fixed_and_closed.md) | 区間の作り方「固定」と閉じたガイド (core だけ。16b の準備) |
| 16b | [16b_select_mode.md](16b_select_mode.md) | 選択のモード (自前の選択 (ハイライト・クリック・ダブルクリックでループ・矩形) を Maya の選択に書き、カット / 縫合・三角形を越えるループ) |
| 17a | [17a_mirror_map.md](17a_mirror_map.md) | 対称の対応表 (cKDTree)・設定 (オン / オフ・空間・軸・許容値)・Maya 優先・ボタンと X キー |
| 17b | [17b_symmetric_selection.md](17b_symmetric_selection.md) | 選択のモードの対称の選択 (反対側も光らせて選ぶ・矩形も両側) |
| 17c | [17c_guide_partners.md](17c_guide_partners.md) | ガイドの相手 (反対側に実物のガイドを作り、どちらを編集しても作り直す)・カット / 縫合は相手にも |
| 18 | [18_auto_apply.md](18_auto_apply.md) | 自動のカット / 縫合 (作成のモードで点を足すたびに、足した区間へ。1 回の Undo) |
| 19 | [19_exit_selection.md](19_exit_selection.md) | ツールを抜けたら、ガイドのエッジを選ぶ (作成・編集のモード。設定で止められる) |
| 20 | [20_context_base.md](20_context_base.md) | コンテキストの基底を MPxContext に・選択のモードを替えられたらエッジの選択モードに戻す |
| 21 | [21_delete_all.md](21_delete_all.md) | パネルの「全削除」(対象のメッシュのガイドをすべて。確認・1 回の Undo) |
| 22 | [22_marking_menu.md](22_marking_menu.md) | パネルの表示の設定・Shift+右クリックのマーキングメニュー |
| 23 | [23_split_context.md](23_split_context.md) | context.py を分ける (TargetWatch・ToolActions) |
| 24 | [24_straightness.md](24_straightness.md) | まっすぐさ (曲がりの少ないパス。向き付きのエッジを節にした dijkstra) |
| 25 | [25_ray_index.md](25_ray_index.md) | レイの索引 (accelParams。MFnMesh を持ち続けて使い回す) |
| 26 | [26_tests.md](26_tests.md) | テストを残す (pytest の決まりの検査・mayapy の core と Maya の流れ) |
| 27 | [27_shortest_only.md](27_shortest_only.md) | 版 1 (最短だけ) と版 2 (UVSeamTool2) に分けた。版 1 に取り込んだもの: 形の上で拾う線・点の挿入・選んだ点をまとめて動かす・切り離す / 接続する |
