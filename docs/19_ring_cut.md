# 段階 19: 輪切り (切る面の境目)

[目次](README.md) ・ 前: [段階 18](18_finishing.md) ・ 次: [段階 20](20_ring_smooth.md)

## 目的

腕などの筒を、画面で横切るように線を描いて、その位置で一周するエッジのループをプレビューし、確定で
「ためる」(自動ならすぐカット)。決めた仕様 (2026-10-12):

| | 仕様 |
|---|---|
| 始め方 | 3 つ目のモード「輪切り」(Tab で パス -> 選択 -> 輪切り) |
| プレビュー | ドラッグ中もずっと |
| 確定 | クリックで確定し、パスの区間と同じく **ためる** (自動 ON ならすぐカット / 縫合) |
| 切る向き | 見たとおり (補正しない) |
| 対称 | 今の仕組みで反対側にも |
| 探し方 | 線とカメラで決まる「切る面」でフェースを 2 つに分け、その境目のエッジ (はじめの案 A は作り直した。下の「経緯」)## 経緯 (案 A からの作り直し)

はじめは **案 A: 今あるループから選ぶ** (線の近くで線と平行なエッジを候補にし、ダブルクリックと同じループを求めて、
閉じた (一周する) ループのうち線に一番沿うもの) で作った。GUI で試すと次の問題があった。

| 問題 | 原因 |
|---|---|
| かなりラグがある | ドラッグのたびに Maya にループを聞く (polySelect。1 本 2 ms ほどを何本も)・表か裏か・点数を Python で 1 本ずつ |
| 三角形などでループにならない | トポロジーが一周のループになっていないと、答えが無い |

ユーザーの「カットを出して調整しながらループの位置を見たいので、かなり高速に」に合わせて、**切る面の境目** に作り直した。

## 仕組み

```
押す    ringPress: メッシュごとに RingTarget (scene/ring.py)
          頂点の画面の位置 (project_points)・頂点の位置の配列
          エッジとフェースの対応 (SectionTopology。MeshModel がトポロジーごとに覚える)
ドラッグ ringDrag -> findRing
          線の両端の視線 2 本 -> 切る面 (plane_from_rays)
          全頂点の面からの距離 -> フェースごとの符号 (頂点の距離の和) -> 両側のフェースにはさまれたエッジ
          -> 画面で線の範囲 (0〜1) のものだけ                   (どれも numpy の配列の計算 1 回ずつ)
離す    ドラッグならプレビューを残す。クリックなら confirmRing (段階 19 の前半と同じ。ためる)
```

- **必ず閉じた輪になる**: 筒をフェースで 2 つに分けた境目なので、三角形・ポール・途切れたループでも一周する
- **見たとおりの位置**: 切る面は線の真下を通り、画面の奥へ伸びる。裏側も同じ面で切れるので、表 / 裏を調べなくてよい
- **線の範囲**: 面の上の点は、画面では線の延長の上に写る。胴体なども面で切れるが、線の範囲の外なので外れる
- **段差**: 斜めに描くと、面に一番近いエッジを通るので段差 (階段) になる。腕の軸に直角に近く描けば、今ある一周の段になる。
  離したときに整える処理は段階 20
- **速さ** (40,200 頂点・一部三角形の円柱): ドラッグ 1 回 1.3〜2.7 ms (案 A は 20〜30 ms)。押したとき 180〜200 ms
  (初めてのとき: グラフとエッジとフェースの対応を作る。2 回目からは画面の位置だけで数十 ms)

## 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/section.py:38](../core/section.py#L38) `plane_from_rays` | 視線 2 本 (始点・向き) を含む平面 (透視でも平行投影でも同じ式) |
| [core/section.py:50](../core/section.py#L50) `SectionTopology` | エッジの両側のフェース。numpy の版は、フェースの角の組の鍵を searchsorted でエッジの番号に直し、1 つ目 / 2 つ目のフェースを並べる (Python の版もある) |
| [core/section.py:116](../core/section.py#L116) `section_edges` | 面からの距離 -> フェースの符号 -> 境目 -> 線の範囲 |
| [core/ring.py](../core/ring.py) `Stroke` | 画面の線 (案 A の候補・点数の関数は取り除いた) |
| [scene/ring.py](../scene/ring.py) `RingTarget` / `RingFound` | メッシュごとの、ドラッグの間は変わらない用意と、見つかったエッジ |
| [scene/mesh.py:284](../scene/mesh.py#L284) `sectionTopology` | エッジとフェースの対応をトポロジーごとに覚える (MFnMesh.getVertices を 1 回) |
| [scene/edit.py](../scene/edit.py) `confirm_ring` / `_push_segment` | 輪切りを区間として積む (パスのスタートは変えない。パスの確定と同じ処理) |
| [tool/ring.py:47](../tool/ring.py#L47) `ringPress` / [:98](../tool/ring.py#L98) `findRing` / `RingMixin` | 押す / ドラッグ / 離す / 確定 / 捨てる。視線は `view_ray` (テストでは差し替え) |
| [tool/context.py](../tool/context.py) | 輪切りのモードの左ボタン・Esc・モードの切り替え |
| [tool/manipulator.py](../tool/manipulator.py) `setRingPreview` | プレビューを描く。輪切りのモードでは頂点 / エッジを拾わない |
| [core/draw_list.py](../core/draw_list.py) `ring_items` / [tool/drawing.py](../tool/drawing.py) `draw_stroke` | ループ (プレビューの色) と「輪切り N 本」/ 画面の白い線 |
| [core/settings.py](../core/settings.py) / [core/actions.py](../core/actions.py) | モード `ring` (Tab で 3 つを巡回)。自動・自動の操作のボタンは輪切りにも |
| [tests/UVPathCut/test_ring.py](../../tests/UVPathCut/test_ring.py) | 面の作り方 (平行投影・透視)・四角形の筒で一周の段・三角形の筒・斜めの線で閉じた輪・線の範囲 |
| [tests/UVPathCut/mayapy/test_ring.py](../../tests/UVPathCut/mayapy/test_ring.py) | Maya の円柱・numpy と Python が同じ・プレビュー -> 確定 / Esc / Undo・自動カット・対称・細かい円柱 (一部三角形) の速さ |

み)

## 落とし穴 (GUI で確認)

- **ドラッグ中にプレビューが出ない**: Maya はツールのドラッグ中、ツール自身の描画 (doDrag の drawMgr) しか描き直さず、
  マニピュレータの drawUI は次にビュー全体を描き直すまで呼ばない (ビューを動かすと出た)。ドラッグ中は、白い線と同じ
  doDrag の drawMgr にプレビューも描く (`UVPathManip.renderRing`)。離したとき・確定したときはビューを 1 回描き直す
- マウスのイベントの中のエラーは表に出にくいので、押す・ドラッグの中のエラーは 1 回の操作につき 1 回、警告に出す
  (`_report_ring_error`)。調べる用に `UVPathCut.diagnose_ring()` (ビューの真ん中に縦の線を引いたとして、
  視線・切る面・境目の数を出す)

## GUI での確認表

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polyCylinder(name="arm", axis=(1, 0, 0), radius=0.5, height=4, subdivisionsAxis=24, subdivisionsHeight=12)
cmds.select("arm")
import UVPathCut; UVPathCut.tool()
# Tab を 2 回 (パス -> 選択 -> 輪切り)
```

| # | 操作 | 期待 |
|---|---|---|
| 1 | 腕を横切るように上から下へドラッグ | 白い線が出て、線に沿う一周のループが黄色で追従する。「輪切り N 本」 |
| 2 | 離す | ループが残る |
| 3 | クリック | 確定してマゼンタ (未実行) になり、エッジが選ばれる。C でカット |
| 4 | Ctrl+Z | 確定が 1 回で戻る |
| 5 | ドラッグ -> Esc | プレビューが消える |
| 6 | 自動 ON で確定 | すぐカットされる (赤) |
| 7 | 対称 (X) で反対側の腕も | 反対側のループもうすく出て、確定で両側 |
| 8 | 腕の外に描く | 何も出ない (離すと「線がメッシュを横切っていません」) |
| 9 | 斜めに描く・斜めから見て描く | 見たとおりの面で一周 (段差になる) |
| 10 | 三角形の混ざったモデル・実際の腕 | 一周が出る。大きいメッシュでもドラッグに遅れずに追従する |
