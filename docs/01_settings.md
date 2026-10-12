# 段階 1: 設定の定義表・保存・コンテキストのコマンドのフラグ

[目次](README.md) ・ 前: [段階 0](00_skeleton.md)

## 目的

- 設定 (拾うもの・自動カット・自動のときの操作) を **定義表 1 か所** で決める
- 値の正規化 (型・選択肢・範囲) と、変わったことの通知を Maya に依存しない形で作る
- optionVar に保存し、Maya を起動し直しても残す
- コンテキストのコマンド (`uvPathCutCtx`) の編集 / 問い合わせのフラグを、定義表から自動で作る

## 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [core/settings.py:31](../core/settings.py#L31) `Setting` | 1 項目の定義 (キー・種類・既定値・短いフラグ・表示名・選択肢・範囲・説明) |
| [core/settings.py:56](../core/settings.py#L56) `DEFINITIONS` | 定義表。今は `pickMode` / `autoCut` / `operation` の 3 つ |
| [core/settings.py:80](../core/settings.py#L80) `normalize` | 値を型・選択肢・範囲に直す。直せなければ `SettingsError` |
| [core/settings.py:124](../core/settings.py#L124) `normalize_all` | 保存していた dict を、使える値だけにする (知らないキーは捨て、壊れた値は既定値) |
| [core/settings.py:141](../core/settings.py#L141) `Settings` | 値を持つ。`set` で正規化 → 保存 → リスナーへ通知。`reset` / `choiceIndex` |
| [scene/prefs.py:23](../scene/prefs.py#L23) `OptionVarStorage` | optionVar `uvPathCutSettings` に JSON で保存 (既定値と違う項目だけ) |
| [tool/context.py:54](../tool/context.py#L54) | コンテキストが作られたときに `Settings(OptionVarStorage())` を持つ |
| [tool/context.py:93](../tool/context.py#L93) `appendSyntax` | 定義表の各項目をフラグとして足す (+ `-resetSettings`) |
| [tool/context.py:100](../tool/context.py#L100) `doEditFlags` | 種類ごとに引数を読み、`settings.set` |
| [tool/context.py:122](../tool/context.py#L122) `doQueryFlags` | 真偽値・小数はそのまま、選択肢は番号で返す |
| [reloader.py](../reloader.py) | `UVPathCut.core.settings` を `MODULES` に、`UVPathCut.scene.prefs` を `MAYA_MODULES` に足した |
| [tests/UVPathCut/test_settings.py](../../tests/UVPathCut/test_settings.py) | 定義表・正規化・通知・既定に戻す (pytest 9 件) |
| [tests/UVPathCut/mayapy/test_prefs.py](../../tests/UVPathCut/mayapy/test_prefs.py) | optionVar の読み書き (mayapy 3 件) |
| [tests/UVPathCut/mayapy/run_all.py](../../tests/UVPathCut/mayapy/run_all.py) | mayapy のテストを、ファイルごとに別のプロセスでまとめて実行 |

## 仕組み

### 定義表から作るもの

```
DEFINITIONS (core/settings.py)
  ├─ normalize / normalize_all    値の正規化 (Maya 不要。pytest)
  ├─ Settings                     値・保存・通知
  ├─ appendSyntax / doEditFlags / doQueryFlags   コンテキストのコマンドのフラグ (tool/context.py)
  └─ ツール設定のウィンドウ         (段階 12)
```

旧版では、設定を 1 つ足すたびに「正規化・フラグの登録・編集・問い合わせ・MEL・`setSetting` の分岐」を
手で書き足していた。今は **定義表に 1 行** 足せば、正規化とフラグがそろう。

### 種類ごとの正規化

| 種類 | 受け付けるもの | フラグの型 | 問い合わせの戻り値 |
|---|---|---|---|
| `BOOL` | `True` / `False`、`1` / `0`、`"true"` / `"on"` / `"yes"` など | `kBoolean` | 真偽値 |
| `CHOICE` | 選択肢の名前、番号 (`0`, `"1"` など) | `kString` | 番号 (`choices` の順) |
| `FLOAT` | 数・数の文字列。範囲の外は端に寄せる | `kDouble` | 小数 |

### Settings の流れ

```
settings.set("pickMode", "0")
  -> normalize: "0" -> "vertex"
  -> 値が変わっていなければ、何もしない (保存も通知もしない)
  -> storage.save(values)      OptionVarStorage: 既定値と違う項目だけを JSON で optionVar に
  -> listener("pickMode", "vertex")   コンテキストの _on_setting_changed がログに出す
```

`Settings` は保存先 (`load()` / `save(dict)` を持つもの) を受け取るだけで、Maya を知らない。
テストでは辞書で代わりをする (`MemoryStorage`)。表示などへの反映は、それぞれの段階で
リスナーを足して行う (設定を変えた側が、何を更新するかを知らなくてよい)。

### コンテキストのコマンドの編集 / 問い合わせ

```python
cmds.uvPathCutCtx("uvPathCutContext", edit=True, pickMode="vertex")   # doEditFlags
cmds.uvPathCutCtx("uvPathCutContext", query=True, pickMode=True)       # doQueryFlags -> 0
```

- `edit` / `query` を付けると、Maya は `makeObj` を呼ばずに、**そのツールを作ったときのコマンドの
  インスタンス** の `doEditFlags` / `doQueryFlags` を呼ぶ。だから `self._context` でツールに届く
- 使えるフラグは `appendSyntax` で足す。`MSyntax.addFlag` の引数の型は 1 つだけ
- 編集で直せない値を渡すと、`RuntimeError` を投げてコマンドのエラーにする (スクリプトエディタに赤字)

### 保存

- optionVar は Maya を閉じるときに `userPrefs.mel` に書かれ、次に起動しても残る
- 値は JSON の文字列 1 つにまとめる (設定を足しても optionVar を増やさずに済む)
- 既定値と同じ項目は書かない。全部が既定値なら optionVar ごと消す
  (既定値を将来変えたとき、保存していない項目は新しい既定値になる)

## 落とし穴

- `MPxContextCommand.setResult` で返せるのは bool / int / float だけ。ドキュメントには文字列も
  あるが、実機では文字列を返すと `kFailure` (Unexpected Internal Failure) になる (ブラシで確認)。
  選択肢は番号で返す
- コンテキストのコマンドは mayapy (standalone) では動かない (コンテキストを作れない)。
  フラグの動きは GUI で確かめる。正規化と保存は pytest / mayapy で確かめた
- テストでユーザーの本当の設定を書き換えないよう、mayapy のテストは別の optionVar の名前を使う

## 試し方

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
import UVPathCut; UVPathCut.tool()          # 「ツールを有効にしました  設定 {...}」

import maya.cmds as cmds
ctx = "uvPathCutContext"
cmds.uvPathCutCtx(ctx, edit=True, pickMode="vertex")     # 「pickMode = 'vertex'」
cmds.uvPathCutCtx(ctx, query=True, pickMode=True)        # 0 (vertex の番号)
cmds.uvPathCutCtx(ctx, edit=True, operation=1)           # 番号でもよい -> 'sew'
cmds.uvPathCutCtx(ctx, edit=True, autoCut=False)
cmds.uvPathCutCtx(ctx, edit=True, pickMode="face")       # エラー (選択肢に無い)
cmds.optionVar(query="uvPathCutSettings")                # 保存された JSON
cmds.uvPathCutCtx(ctx, edit=True, resetSettings=True)    # 既定に戻す (optionVar も消える)
```
