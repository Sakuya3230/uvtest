# 段階 16b: 選択のモード (エッジを選んで、そのままカット / 縫合)

## 目的

3 つ目のモード「選択」。エッジを選び、選んだエッジにそのままカット / 縫合を当てる (ガイドは作らない。描くだけ)。
選択の計算は自前で行い、**結果は Maya の選択に書く** (cmds.select。Maya と同じく Undo に載る)。

| 操作 | 動き |
|---|---|
| マウスを乗せる | マウスの下のエッジを光らせる (設定 `hoverEdgeColor`) |
| クリック | 光っているエッジを選ぶ (なし = 置き換え / Shift = 切り替え / Ctrl = 外す / Ctrl+Shift = 足す) |
| ダブルクリック | 光っているエッジのループ (三角形も越える) を選ぶ (なし = 置き換え / Shift = 足す / Ctrl = 外す) |
| 何も無い所をクリック | 選択を外す |
| ドラッグ | 枠を描き、離したときに Maya の矩形選択 (`MGlobal.selectFromScreen`。隠れたものは選ばない) |
| L / パネルの「ループ」 | ループの事前ハイライト。オンの間はマウスの下のループを光らせ (設定 `loopColor`)、クリックでそのループを選ぶ |
| C / S | 選んでいる、対象のメッシュのエッジをカット / 縫合 (メッシュにまたがっても 1 回の Undo) |

左ボタンはすべてこのサブツールが受け取る。Maya の事前選択のハイライト・ダブルクリックの機能は使わない (下の「経緯」)。

## 決めたこと (ユーザーの選択)

- 選んだエッジは Maya の選択に持つ (ツールを抜けても・UV エディタでもそのまま使える)
- 矩形は Maya の矩形選択を呼ぶ (隠れたエッジは選ばない。矩形には事前のハイライトが無いので、食い違いは起きない)
- 対称の選択は、対称の段階で作る (それまでは無い)
- **光らせるのと選ぶのを同じ計算で決める** (マウスの下のエッジ `SelectPicker.edgeAt`・ループ `EdgeTopology.edgeLoop`)

## ループの決まり (三角形を越える)

| 進んできた先の頂点 | 次のエッジ |
|---|---|
| 今のエッジが縁 | 縁に沿って、次の縁のエッジ (Maya のダブルクリックと同じ) |
| 辺の数が 4 で、まわりに三角形が無い (四角形の格子) | 面を共有しない、ちょうど 1 本の辺 |
| まわりに三角形があり、辺の数が 6 以下 | 面を共有しない辺のうち、いちばんまっすぐ続く辺 (45 度より曲がるなら止まる) |
| それ以外 (ポールなど) | 止まる |

辺の数を 6 以下に限るのは、球の極 (三角形が 20 枚集まる) を越えて経線が反対側までつながらないようにするため。

## 流れ

```
マウスを動かす -> SelectTool.hover -> SelectPicker.edgeAt -> _update_lit (エッジ 1 本か、ループ)   光らせる = クリックで選ぶもの
押す -> 受け取る (押した位置と修飾キーを覚える)
ドラッグ -> 4 ピクセル以上動いたら枠を描く
離す -> 枠があれば utils.selection.select_in_rect   (selectFromScreen -> 選ぶ前に戻して cmds.select で書き直し、Undo に載せる)
        光っているものがあれば select_edges (cmds.select)
        何も無ければ clear_selection
ダブルクリック (ViewInputFilter が受け取る。2 回目の押下はコンテキストに届かない) -> SelectTool.doubleClick -> ループを select_edges
C / S -> selected_edges (対象のメッシュだけ) -> uv_apply.apply_selected_edges (undo.chunk で 1 回の Undo)
```

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [core/path/edge_topology.py](../core/path/edge_topology.py) | `EdgeTopology`: 頂点 -> エッジ・エッジ -> 面・面 -> エッジ・面の頂点の数。`edgeLoop(edge, positions)` |
| [utils/picking.py](../utils/picking.py) | `pick_face(meshes, x, y)` (`pick_vertex` と同じ表の面の決め方) |
| [utils/selection.py](../utils/selection.py) | `selected_edges`・`select_edges`・`clear_selection`・`select_in_rect` (17b で `edges_in_rect` に変えた)・`click_mode` / `double_click_mode` (修飾キー -> 選び方) |
| [tool/target_mesh.py](../tool/target_mesh.py) | `edges()`・`faceVertices()`・`worldPoints()`・`edgeTopology()` (初めて使うときに作り、トポロジーが変わったら捨てる) |
| [tool/select_picker.py](../tool/select_picker.py) | `SelectPicker.edgeAt` (表の面に当たった点に、いちばん近いその面のエッジ) |
| [tool/select_tool.py](../tool/select_tool.py) | `SelectTool` |
| [tool/view_input.py](../tool/view_input.py) | ダブルクリックを受け取る (`double_click`)。受け取ったら、続く左ボタンの離しも Maya に渡さない |
| [tool/sub_tool.py](../tool/sub_tool.py) | `doubleClick(x, y, shift, ctrl)`。作成・編集は受け取って捨てる |
| [tool/uv_apply.py](../tool/uv_apply.py) | `apply_edges`・`apply_selected_edges` |
| [tool/painter.py](../tool/painter.py) | `segments(線分の列)` (1 回の `lineList`) |
| [tool/actions.py](../tool/actions.py) / [tool/context.py](../tool/context.py) / [ui/icons.py](../ui/icons.py) | モード「選択」・トグル「ループ」(L)・Tab の順・アイコン |
| [core/settings/definitions.py](../core/settings/definitions.py) | `hoverEdgeColor`・`loopColor` |

## 経緯 (遠回りの記録)

1. 最初は「エッジを自前で選んで Enter でガイドにする・C / S はガイドにしてから当てる」形で作った。ユーザーの見直しで
   「ガイドを作らず、選んだエッジにそのまま当てる」形にした (選んだエッジを頂点の列にする処理などは消した。段階 16a の
   `guide_from_path` は SeamGuide の「境界をガイドに」用に残した)
2. 次に、選択を Maya の普通の選択 (コンテキストの基底) に任せた。ダブルクリックでループが選べなかった (2 回目の押下が
   `doPress` に届かない) ので、`MPxSelectionContext.setAllowDoubleClickAction()` を使った (ユーザーの指摘。同じクラスに
   `setAllowPreSelectHilight` (toolOnSetup で呼ぶ決まり)・`setAllowSymmetry`・`setAllowSoftSelect`・`setAllowPaintSelect`
   (2027 だけ) もある。どれも引数なしで「有効にする」だけ。`__init__` で呼ぶと kFailure (Object does not exist))
3. ところが事前選択のハイライトは、作成・編集のモードにも出てしまう (モードごとに切れない)。ユーザーの判断で、選択を
   自前で作る今の形にした。光らせるのと選ぶのを同じ計算にしたので、食い違わない

## 落とし穴

- `MGlobal.selectFromScreen` は Undo に積まれない。選ぶ前の選択に戻してから、結果を cmds.select で書き直す
- Maya の事前選択のハイライトは、プリファレンス (選択項目の「事前選択のハイライト」。`selectPref -preSelectHilite`) が
  オフだと標準の選択ツールでも出ない (今は使っていない)
- 三角形を越える決まりは「まっすぐさ」で選ぶので、形によっては思わない辺へ進むことがある (45 度より曲がる所では止まる)
- 対称の選択は 17b で足した ([17b_symmetric_selection.md](17b_symmetric_selection.md))

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polyPlane(sx=6, sy=6); cmds.polyTriangulate("pPlane1.f[14]"); cmds.select("pPlane1"); UVSeamTool.tool()
# [選択] -> マウスの下のエッジが光る -> クリックで選ぶ / ダブルクリックでループ (三角形を越える) / 矩形
# L -> ループが光る -> クリックでループを選ぶ / C でカット -> Ctrl+Z / [作成]・[編集] では何も光らない
```

mayapy で、クリックでエッジ・ダブルクリックでループ・Undo で戻る・ループの事前ハイライト中の Ctrl+クリックで外す・
何も無い所のクリックで外す・修飾キーと選び方の対応、三角形を越えるループ (平面の一部を三角形に割っても横・縦ともつながる。
球の極は越えない) を確かめた (マウスの下のエッジを拾う所は差し替えた。矩形の selectFromScreen は GUI で)。
