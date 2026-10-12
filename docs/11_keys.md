# 段階 11: キー

[目次](README.md) ・ 前: [段階 10](10_actions_and_buttons.md)

## 目的

- 操作の表 (段階 10) にキーの項目を足し、キーの受け取りを表から作る
- ツールを使っている間だけ、マウスが 3D ビューの上にあるときだけ受け取る (それ以外は Maya にそのまま)

| キー | 操作 |
|---|---|
| Tab | 拾うもの (頂点 / エッジ) の切り替え |
| C | ためた区間をまとめてカット |
| S | ためた区間をまとめて縫合 |
| Shift+Esc | クリア (リセット) |
| Esc | スタートの取り消し (今までどおり Maya がコンテキストの `abortAction` を呼ぶ) |

自動の切り替え (自動 ON / OFF・自動の操作) にはキーを付けない (旧版で決めた)。

## 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/actions.py:48](../core/actions.py#L48) `KeyBinding` | キー (Qt のキーの名前と Shift / Ctrl)。`text()` で「Shift+Esc」 |
| [core/actions.py:99](../core/actions.py#L99) 〜 | 操作の表の各行に `key=KeyBinding(...)` |
| [core/actions.py:139](../core/actions.py#L139) `key_bindings` / [:148](../core/actions.py#L148) `key_help` | キーの一覧 (同じキーが 2 つあればエラー) / ヘルプの文字 |
| [tool/keys.py:58](../tool/keys.py#L58) `install` / [:96](../tool/keys.py#L96) `uninstall` | Qt のイベントフィルターを付ける / 外す |
| [tool/keys.py:40](../tool/keys.py#L40) `qt_key_table` | 表から {(Qt のキー, Shift, Ctrl): 操作の ID} |
| [tool/keys.py:47](../tool/keys.py#L47) `pointer_over_view` | マウスが 3D ビューの上で、文字の入力中でないか |
| [tool/context.py:119](../tool/context.py#L119) / [:123](../tool/context.py#L123) | ツールを有効にしたら付け、無効にしたら外す |
| [tool/context.py:101](../tool/context.py#L101) | ヘルプライン (Maya の下の欄) にキーの説明 (表から) |
| [tests/UVPathCut/test_actions.py](../../tests/UVPathCut/test_actions.py) | キーの一覧・重複・ヘルプ (pytest 1 件) |
| [tests/UVPathCut/mayapy/test_keys.py](../../tests/UVPathCut/mayapy/test_keys.py) | QKeyEvent を渡して受け取り方を確かめる (mayapy 3 件。PySide2 / PySide6) |

## 仕組み

### Qt のイベントフィルター

API 2.0 のコンテキストにはキーのイベントが無い (Esc だけは `abortAction` が呼ばれる)。
そこで Qt のアプリケーションにイベントフィルターを付けて、Maya のウィジェットに届く前のキーを見る。

```
キーを押す
  -> Qt が ShortcutOverride を送る   (「このキーをショートカットに使ってよいか」の問い合わせ)
       表のキーで、ビューの上なら accept (ホットキー C / S などより先に受け取る)
  -> Qt が KeyPress を送る
       表のキーで、ビューの上なら runAction(ID) を呼んで消費する (押しっぱなしの繰り返しは実行しない)
  それ以外のキー・ビューの外・文字の入力中 -> False を返して Maya にそのまま渡す
```

- 修飾キーは表のとおりのときだけ受け取る (C は修飾キーなし、クリアは Shift+Esc)。Alt などの
  表に無い修飾キーが付いていれば受け取らない (Maya の Alt の操作を邪魔しない)
- Tab は Qt ではフォーカスの移動に使われるが、アプリケーションのフィルターで先に消費すれば動かない
- Esc (修飾キーなし) は受け取らない。Maya がコンテキストの `abortAction` を呼ぶ (スタートの取り消し)

### 付けている間だけ

フィルターはツールを有効にしたとき (`toolOnSetup`) に付け、無効にしたとき (`toolOffCleanup`) に外す。
外さないと、ツールを抜けても C / S を取り続け、リロードしたあとは古いコードが呼ばれ続ける。
リロード (`reload_modules`) とプラグインの読み直しは、先にツールのコンテキストを消すので、そこで外れる。

### テスト

mayapy でも Qt のアプリケーションはあるので、フィルターを付けて `QKeyEvent` を作り、`eventFilter` に
直接渡して確かめる。マウスがビューの上かの判定 (`eligible`) はテストで差し替える。
修飾キーの扱いが PySide2 (2022) と PySide6 (2027) で違うことがあるので、両方で確かめた。

## 落とし穴

- Maya のホットキーより先に受け取るには、KeyPress ではなく ShortcutOverride を accept する
- フィルターを外し忘れると、ツールを抜けてもキーを取り続ける
- 押しっぱなしの繰り返し (`isAutoRepeat`) で何度も実行しない (消費だけして実行しない)

## 試し方

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polySphere()
import UVPathCut; UVPathCut.tool()
# ヘルプライン (Maya の下の欄) に「Tab 頂点 / エッジ  C まとめてカット ...」
# 1. ビューの上で Tab: 頂点 / エッジが切り替わり、ボタンの文字も変わる (フォーカスは動かない)
# 2. 「自動 OFF」でためてから C / S でまとめて実行。S でキーフレームが打たれない
# 3. Shift+Esc でクリア。Esc だけならスタートの取り消し
# 4. マウスをビューの外 (スクリプトエディタなど) に出すと、Tab / C / S は普段どおり。ツールを抜けたあとも
```
