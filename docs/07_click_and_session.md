# 段階 7: クリックとセッション (スタート・プレビュー・Esc)

[目次](README.md) ・ 前: [段階 6](06_draw_list.md)

## 目的

- メッシュの上のクリックでスタートを決め、マウスの下までの最短パスをプレビューする
- スタートを決めたときに 1 回だけ探し (段階 5 の PathTree)、ホバーでは道をたどるだけにする
- メッシュの上の修飾キーなしの左クリックはこのツールが受け取り、それ以外は普通の選択のままにする
- Esc でスタートを取り消す

2 回目のクリックは、この段階ではパスをスクリプトエディタに出して、エンドを次のスタートにするだけ
(シーンの変更と Undo は段階 8)。

## 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/session.py:46](../core/session.py#L46) `PathSession` | グラフ・未確定のスタート・そのスタートの PathTree |
| [core/session.py:59](../core/session.py#L59) `setStart` | スタートを決め、PathTree を作る (同じスタートなら作り直さない) |
| [core/session.py:75](../core/session.py#L75) `pathTo` | スタートからゴールまで (木をたどるだけ) |
| [core/session.py:21](../core/session.py#L21) `waypoint_of` / [:26](../core/session.py#L26) `waypoint_label` / [:31](../core/session.py#L31) `preview_label` | 拾ったもの → 端点 / 端点の名前 / エンドの候補に添える文字 (本数と長さ) |
| [tool/context.py:94](../tool/context.py#L94) | ツールに入ったときに `PathSession` を作る (使う計算 scipy / Python をログに出す) |
| [tool/context.py:120](../tool/context.py#L120) `doPress` / [:127](../tool/context.py#L127) `doDrag` / [:132](../tool/context.py#L132) `doRelease` | 受け取るなら基底を呼ばない。受け取らないなら基底 (普通の選択) |
| [tool/context.py:114](../tool/context.py#L114) `_wants_click` | 受け取るか (修飾キーなしの左クリックで、メッシュの上) |
| [tool/context.py:139](../tool/context.py#L139) `_click` | スタートにする / パスを出してエンドを次のスタートにする |
| [tool/context.py:169](../tool/context.py#L169) `abortAction` | Esc でスタートを取り消す |
| [tool/manipulator.py:78](../tool/manipulator.py#L78) `updatePreview` | スタートからマウスの下までの道を引き直す |
| [tool/manipulator.py:135](../tool/manipulator.py#L135) `drawItems` | パス (下)・スタート・マウスの下 (上) の順の描画の一覧 |
| [tests/UVPathCut/test_session.py](../../tests/UVPathCut/test_session.py) | 探す回数・取り消し・文字 (pytest 3 件) |

## 仕組み

### クリックを受け取るか、普通の選択にするか

`MPxSelectionContext` は、マウスの処理 (`doPress` / `doDrag` / `doRelease`) を基底のメソッドで行うと
普通の選択ツールと同じに動く。上書きして **基底を呼ばなければ、選択は変わらない**。

```
doPress
  受け取る (マニピュレータが頂点 / エッジを拾っている・修飾キーなしの左)  -> 基底を呼ばない
  受け取らない (メッシュの外・Shift / Ctrl・中ボタンなど)                -> MPxSelectionContext.doPress(self, ...)
doDrag    受け取ったなら何もしない (矩形選択の枠も出さない)
doRelease 受け取ったなら _click (離したときのマウスの下のもので決める)
```

押したかどうか (`_consumed`) を押してから離すまで覚えておき、3 つのメソッドで同じ判断をする
(押したときだけ受け取って、離したときに基底を呼ぶ、という食い違いを防ぐ)。

基底は `omui.MPxSelectionContext.doPress(self, event, drawMgr, context)` と明示して呼ぶ
(ウェイトスライダーで確認した書き方)。

### スタートとプレビュー

```
1 回目のクリック -> session.setStart(端点)       ここで PathTree を作る (scipy なら全頂点まで探す)
マウスを動かす     -> 拾ったものが変わったら manip.updatePreview()
                       -> session.pathTo(マウスの下)   木をたどるだけ
2 回目のクリック -> パスをログに出し、session.setStart(エンド)  (エンドが次のスタート)
Esc              -> session.clearStart()
```

スタートが変わったとき (`_click` / `abortAction`) は、コンテキストの `refresh` がマニピュレータに
プレビューを引き直させて、ビューを描き直す。

### 描く順

`drawItems` は、パスのプレビュー (黄、layer 1.5) → スタート (緑、2.0) → マウスの下の面と拾ったもの
(橙、2.0) の順に一覧を作る。エンドの候補の文字には、パスのエッジの本数と長さを添える
(`preview_label`。つながっていなければ「つながっていない」)。

## 落とし穴

- API 2.0 のコンテキストは、基底を呼ばなければ選択が変わらない (旧版で確認)。ただし doPress だけ
  受け取って doRelease で基底を呼ぶと、選択ツールの状態が食い違う。3 つで同じ判断をする
- Esc でコンテキストの `abortAction` が呼ばれる (旧版で確認)。マニピュレータのドラッグ中は呼ばれない
  (ウェイトスライダーで確認。このツールはマニピュレータをドラッグしないので関係ない)
- スタートを決めるだけのクリックは Undo に積まない (段階 8 で、確定だけを Undo に積む)

## 試し方

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds
cmds.polySphere(subdivisionsAxis=300, subdivisionsHeight=150)   # 大きめでもホバーが軽いか
import UVPathCut; UVPathCut.tool()   # 「最短パスの計算: scipy (...)」
# 1. クリック: スタートが緑に。マウスを動かすと黄のパスが追い、e[..]  12 本 / 長さ ... と出る
# 2. もう一度クリック: スクリプトエディタに「パス ...」、そこが新しいスタート
# 3. Esc: スタートが消える
# 4. メッシュの外のクリック・Shift / Ctrl のクリック・矩形は普通の選択
```
