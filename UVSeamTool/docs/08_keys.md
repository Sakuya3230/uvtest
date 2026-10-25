# 段階 8: キー

## 目的

パネルのボタンと同じ操作を、キーでもできるようにする。

| キー | 動き |
|---|---|
| Tab | 作成 <-> 編集 |
| C | カット (作成: 作成中のガイド / 編集: 選んでいるガイド) |
| S | 縫合 |

Maya より先にキーを取るのは、次のときだけ。それ以外は今までどおり Maya のキー (ホットキー) になる。

- マウスが 3D のビューの上にある (`QApplication.widgetAt(QCursor.pos())` がビューの描画面か、その子)
- 文字を打つ欄 (QLineEdit・QTextEdit・QPlainTextEdit・スピンボックス) にフォーカスが無い
- 修飾キー (Ctrl / Shift / Alt) を押していない (Ctrl+S の保存などは Maya に渡す)

押しっぱなしの繰り返しは、取るだけで実行しない。

## 流れ

```
キーを押す -> ViewInputFilter.eventFilter (QApplication に付けたフィルター)
  ShortcutOverride  条件がそろえば event.accept() して True    Maya のホットキーより先に、次の KeyPress を受け取る
  KeyPress          条件がそろえば、表の関数を呼んで True
     -> Context._key_command(操作) -> Context._on_action(操作)   パネルのボタンと同じ入り口
          TOGGLE_MODE -> 今と違うモードに / CUT・SEW -> 今のサブツールの applyOperation
```

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [tool/actions.py](../tool/actions.py) | `KEY_ACTIONS` (キーの名前 -> 操作)・`TOGGLE_MODE`・ヘルプにキーを足した |
| [tool/view_input.py](../tool/view_input.py) | `shortcuts` を受け取り、条件がそろったときだけキーを取る (`_filter_shortcut`・`_typing`) |
| [tool/context.py](../tool/context.py) | 表から `shortcuts` を作ってフィルターに渡す。`_on_action` が `TOGGLE_MODE` を受け取る |

## 仕組み

- **キーの表**: `KEY_ACTIONS` に 1 行足せばキーが増える。名前は Qt の `Key_` のあとの部分 (`"Tab"`・`"C"`)。Shift 付きは `"Shift+A"` (段階 18 で足した)
- **ShortcutOverride で先に取る**: Qt は KeyPress の前に ShortcutOverride を送り、ここで accept されたキーは
  ショートカット (Maya のホットキー) にならず、KeyPress として届く。取らないキーは何もせず Maya に渡す
- **ボタンとキーは同じ入り口**: どちらも `Context._on_action(操作)` を呼ぶ。操作の中身は 1 か所だけ

## 落とし穴

- `event.modifiers()` が NoModifier のときだけ取る (Shift+C などは取らない。必要なら表を広げる)
- マウスがパネル (Qt のボタン) の上にあるときは、ビューの上ではないので取らない
- Tab はビューの上では Maya が使っていないが、ほかのウィンドウではフォーカスの移動に使う (ビューの上だけなので影響しない)

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()
# ビューの上で Tab -> パネルの「編集」が選ばれる / もう一度 Tab -> 作成
# 作成で点を置いて C -> カット / 編集でガイドを選んで S -> 縫合
# Ctrl+S -> いつもどおりシーンの保存 / スクリプトエディタで C を打つ -> 文字が入る
```

mayapy (offscreen。2022 / 2027) で、条件がそろったときだけ取る (ShortcutOverride の accept・KeyPress で実行・
繰り返しは実行しない・修飾キー・ほかのキー・ビューの外・文字を打つ欄では取らない) ことを確かめた。
