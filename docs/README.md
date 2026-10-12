# UVPathCut 解説

頂点 / エッジのあいだの最短パスをプレビューして確定し、UV をカット / 縫合するツール。

**使い方は [USAGE.md](USAGE.md)**。ゼロから作る手引きは [tutorial/README.md](tutorial/README.md)。
このページから下は、作り方の記録 (段階ごとの解説。遠回りも含む)。
旧 1 ファイル版 ([plug-ins/old/uvPathCut_v1.py](../../../plug-ins/old/uvPathCut_v1.py)) を、
仕組みを確かめながら段階的にパッケージへ作り直している。

```python
import UVPathCut
UVPathCut.tool()                                   # プラグインを読み込んで、このツールにする

import UVPathCut.reloader as r; r.reload().reload_modules()  # 開発中のリロード
```

## 構成

| 場所 | 役割 | 依存してよいもの | テスト |
|---|---|---|---|
| [constants.py](../constants.py) | プラグインとパッケージが共有する名前 | なし | pytest |
| [log.py](../log.py) | スクリプトエディタへのメッセージ | (warning の中でだけ maya) | pytest |
| [core/](../core/__init__.py) | Maya に依存しない計算 | なし | pytest (Python 3.7) |
| [scene/](../scene/__init__.py) | Maya のシーンを読む / 変える | maya・core | mayapy |
| [tool/](../tool/__init__.py) | 操作と表示 (コンテキスト・マニピュレータ・描画・キー) | maya・Qt・scene・core | GUI |
| [api.py](../api.py) | 公開 API | (関数の中で maya) | mayapy |
| [reloader.py](../reloader.py) | 依存順のリロード | - | pytest |
| [plug-ins/uvPathCut.py](../../../plug-ins/uvPathCut.py) | 登録だけのプラグイン | パッケージ | mayapy |

依存の向きは `tool -> scene -> core` の一方向。
[tests/UVPathCut/test_dependencies.py](../../tests/UVPathCut/test_dependencies.py) が検査する。

## テスト

```
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest scripts/tests/UVPathCut
"C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe" scripts\tests\UVPathCut\mayapy\run_all.py   # mayapy のテストをファイルごとに別プロセスで。2022 でも
```

## 進め方のルール

段階ごとに、目的 → 仕組みの説明 → 実装 → テスト → 解説ページ → GUI での確認の順に進める。
各ページには、目的・追加 / 変更した箇所 (リンク)・仕組み・落とし穴・試し方を書く。

## 段階

| 段階 | ページ | 内容 |
|---|---|---|
| 0 | [00_skeleton.md](00_skeleton.md) | パッケージの骨組み・リロード・登録だけのプラグイン・ツールのコマンド |
| 1 | [01_settings.md](01_settings.md) | 設定の定義表・保存・コンテキストのコマンドのフラグ |
| 2 | [02_target_mesh.md](02_target_mesh.md) | 対象メッシュとエッジの選択モード |
| 3 | [03_mesh_model_and_hover.md](03_mesh_model_and_hover.md) | MeshModel とマウスの下の面 (マニピュレータの doMove) |
| 4 | [04_picking.md](04_picking.md) | 頂点 / エッジを拾う |
| 5 | [05_graph_and_path.md](05_graph_and_path.md) | グラフと最短パス (numpy / scipy) |
| 6 | [06_draw_list.md](06_draw_list.md) | 描画の一覧と描画 |
| 7 | [07_click_and_session.md](07_click_and_session.md) | クリックとセッション (スタート・プレビュー・Esc) |
| 8 | [08_confirm_and_undo.md](08_confirm_and_undo.md) | 確定と Undo (変更のリスト・選択) |
| 9 | [09_cut_and_sew.md](09_cut_and_sew.md) | カット / 縫合・自動カット・まとめて実行 |
| 10 | [10_actions_and_buttons.md](10_actions_and_buttons.md) | 操作の表とボタン、リセット |
| 11 | [11_keys.md](11_keys.md) | キー |
| 12 | [12_tool_settings_window.md](12_tool_settings_window.md) | ツール設定のウィンドウ |
| 13 | [13_external_changes.md](13_external_changes.md) | 外部の変更の検知 (位置・トポロジー・名前)、トポロジーごとのセッション |
| 14 | [14_multiple_meshes.md](14_multiple_meshes.md) | 複数のメッシュ (対象の集まり・スタートは全体で 1 つ・全メッシュをまとめて実行) |
| 15 | [15_straightness.md](15_straightness.md) | 曲がりの重み (向き付きのエッジの状態・scipy の状態の疎行列) |
| 16 | [16_select_mode.md](16_select_mode.md) | 選択のモード (16a 切り替え・クリックの振り分け・ダブルクリック / 16b 選択のカット / 縫合 / 16c ループのプレビュー) |
| 17 | [17_symmetry.md](17_symmetry.md) | シンメトリ (17a 対応表・面・使い回し / 17b パス / 17c 選択 / 17d ボタンとキー) |
| 18 | [18_finishing.md](18_finishing.md) | 仕上げ (コンテキストの分割・扱えないメッシュ・使い方のページ) |
| 19 | [19_ring_cut.md](19_ring_cut.md) | 輪切り (3 つ目のモード・線・切る面の境目・ためる) |
| 20 | [20_ring_smooth.md](20_ring_smooth.md) | 輪切りをなめらかにする (離したときに、今あるループに吸い付ける / 面に沿う道に引き直す) |
| 21 | [21_ring_adjust_and_seam.md](21_ring_adjust_and_seam.md) | 輪切りの微調整 (ホイールでずらす / 傾ける) と縦の継ぎ目 (Shift+ドラッグ・奥側だけ) |

保留中の案 (UV エディタでの操作。輪切りのあとに決める): [ideas.md](ideas.md)
