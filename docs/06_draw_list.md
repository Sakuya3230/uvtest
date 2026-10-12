# 段階 6: 描画の一覧と描画

[目次](README.md) ・ 前: [段階 5](05_graph_and_path.md)

## 目的

- 「**何を描くか**」(面・拾ったもの・パス・スタート…) と「**どう描くか**」(MUIDrawManager の呼び出し・
  色の変換・カメラへ寄せる) を分ける
- 何を描くかを Maya に依存しない形 (描画の一覧) にして、pytest で確かめる
- 見た目 (色・太さ・手前に出す度合い) を役割ごとの表 (`THEME`) 1 か所にまとめる

見た目は段階 4 と同じ (作り替えても表示が変わらないことを確かめる段階)。
パスのプレビューを実際に描くのは、スタートをクリックで決める段階 7。

## 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/draw_list.py:34](../core/draw_list.py#L34) `ROLE_*` | 役割 (面の塗り・面の縁・拾ったもの・パス・スタート・文字) |
| [core/draw_list.py:42](../core/draw_list.py#L42) `Style` / [:54](../core/draw_list.py#L54) `THEME` | 役割の見た目 (色・不透明度・線の太さ・点の大きさ・手前に出す度合い) |
| [core/draw_list.py:78](../core/draw_list.py#L78) `DrawList` | 描くものの一覧 (`lines` / `loop` / `polygon` / `point` / `text`) |
| [core/draw_list.py:133](../core/draw_list.py#L133) `hover_items` | マウスの下の面と、拾った頂点 / エッジ・番号 |
| [core/draw_list.py:144](../core/draw_list.py#L144) `path_items` | パスのエッジの線 (1 つの項目にまとめる) |
| [core/draw_list.py:119](../core/draw_list.py#L119) `waypoint_items` / [:153](../core/draw_list.py#L153) `endpoint_points` | 端点 (点か線) と文字 / 端点の位置 |
| [tool/drawing.py:122](../tool/drawing.py#L122) `render` | 一覧を MUIDrawManager で描く (寄せる・色の変換・種類ごとの呼び出し) |
| [tool/drawing.py:109](../tool/drawing.py#L109) `_merged` | 続いている同じ役割の線 / 三角形を 1 回の呼び出しにまとめる |
| [tool/manipulator.py:109](../tool/manipulator.py#L109) `drawItems` / [:113](../tool/manipulator.py#L113) `drawUI` | 一覧を作って `render` に渡すだけ |
| [tests/UVPathCut/test_draw_list.py](../../tests/UVPathCut/test_draw_list.py) | 一覧の中身 (pytest 6 件) |
| [tests/UVPathCut/mayapy/test_drawing.py](../../tests/UVPathCut/mayapy/test_drawing.py) | まとめ方 (mayapy 2 件) |

## 仕組み

### 分け方

```
UVPathManip.drawUI
  -> drawItems()                      何を描くか (core.draw_list。Maya 不要)
       hover_items(pick)                面の塗り (faceFill)・面の縁 (faceEdge)・拾ったもの (pick)・番号 (label)
       (段階 7 から) path_items / waypoint_items
  -> render(drawMgr, 一覧, 目, 設定)    どう描くか (tool.drawing。MUIDrawManager を呼ぶのはここだけ)
       役割 -> THEME の Style
       点をカメラへ (EYE_OFFSET x layer) 寄せる
       色をカラーマネジメントの逆変換に通す (文字はそのまま)
       種類ごとに point / mesh(kLines / kClosedLine / kTriangles) / text
```

### 描画の一覧 (DrawList)

項目 (`DrawItem`) は「種類・役割・点のリスト・文字」だけを持つ。

| 種類 | 意味 | MUIDrawManager |
|---|---|---|
| `LINES` | 線分の集まり (2 点ずつ) | `mesh(kLines)` |
| `LOOP` | 閉じた折れ線 | `mesh(kClosedLine)` |
| `TRIANGLES` | 三角形の集まり (3 点ずつ。`polygon` が扇形に分ける) | `mesh(kTriangles)` |
| `POINT` | 点 | `point` |
| `TEXT` | 文字 (画面を向く) | `text` |

### 役割と見た目 (THEME)

```python
THEME = {
    ROLE_FACE_FILL: Style((0.35, 0.95, 0.45), alpha=0.15, layer=1.0),
    ROLE_PATH:      Style((1.00, 0.85, 0.20), width=4.0, layer=1.5),
    ROLE_PICK:      Style((1.00, 0.60, 0.15), width=5.0, size=12.0, layer=2.0),
    ...
}
```

`layer` は「カメラへ寄せる度合い」。面の縁 (1.0) < パス (1.5) < 拾ったもの・スタート (2.0) の順に
手前になるので、重なっても上の役割が隠れない。

### まとめて描く

パスは何百本ものエッジになる。`path_items` は 1 つの `LINES` にまとめ、`render` はさらに
続いている同じ役割の `LINES` / `TRIANGLES` をまとめるので、MUIDrawManager の呼び出しは役割ごとに 1 回で済む。
間に別の役割があるときは、描く順 (上下の重なり) を保つためにまとめない。

## 落とし穴

- 文字 (`text`) の色はカラーマネジメントの変換を通らないので、逆変換せずにそのまま渡す
- 点・線・三角形を面にそのまま重ねると、奥行きの比べ合いで負けてちらつく。カメラへ寄せる量は
  カメラまでの距離に比例させる (遠くでも近くでも効く)
- MUIDrawManager は描画の最中 (`drawUI`) にしか無いので、`render` そのものは mayapy では試せない。
  一覧の中身 (pytest) とまとめ方 (mayapy) を確かめ、見た目は GUI で確かめる

## 試し方

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polySphere()
import UVPathCut; UVPathCut.tool()
# 段階 4 と同じ見た目: 面がうすい緑、拾ったエッジが橙の太線、e[番号]

# 見た目は THEME だけで変えられる (試したら元に戻す):
# core/draw_list.py の ROLE_PICK の色を (0.2, 0.6, 1.0) にして保存 -> r.reload().reload_modules(); UVPathCut.tool()
```
