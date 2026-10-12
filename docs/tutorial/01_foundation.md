# 1. 土台 (手順 1〜3)

[目次](README.md) ・ 次: [2. メッシュと表示](02_mesh_and_view.md)

## 手順 1: パッケージ・薄いプラグイン・リロード

**ゴール**: Maya で `import UVPathCut; UVPathCut.tool()` でツールになり、コードを直したらリロードだけで反映される。

**作るもの**

| ファイル | 中身 |
|---|---|
| `constants.py` | プラグイン名・コマンド名 (`uvPathCutCtx` など)・ノード名・`PLUGIN_COMMANDS` / `PLUGIN_NODES` |
| `log.py` | `info` / `warning` (頭に「UV パスカット:」) |
| `reloader.py` | 依存順の `MODULES` (Maya 不要) / `MAYA_MODULES`、`reload()` (自分を読み直して返す)、`reload_modules()` |
| `api.py` | `load_plugin` / `tool` / `reload_modules` / `ensure_plugin_current` |
| `plug-ins/uvPathCut.py` | `initializePlugin` で登録するだけ |

**方法**

- プラグインの creator は、**呼ばれるたびに `importlib.import_module` でパッケージのクラスを引いて作る**。
  クラスを直接登録すると、パッケージをリロードしても古いクラスのインスタンスが作られ続ける
  ```python
  def _create_context_command():
      return importlib.import_module("UVPathCut.tool.context").UVPathCutContextCommand()
  ```
- `reloader.reload()` は reloader 自身を `importlib.reload` して**新しいモジュールを返す**。
  `import UVPathCut.reloader as r; r.reload().reload_modules()` の形にすると、追加したモジュールの一覧も新しくなる
- `reload_modules()` は先にツールのコンテキストを消す (`deleteUI(..., toolContext=True)`)。コンテキストのインスタンスは
  作ったときのクラスのままなので、消して作り直さないと古いコードが動き続ける
- コマンド・ノードの登録は `initializePlugin` のときだけ。新しいコマンドを足したら、リロードの最後に
  「登録されていないものがあればプラグインを読み直す」(`hasattr(cmds, 名前)` で調べる。`pluginInfo -command` には
  コンテキストのコマンドが出ない)
- クラスでは**引数なしの `super()`** を使う。`super(クラス, self)` は、リロード後に古いインスタンスへイベントが届くと TypeError

**確かめ方**: mayapy でプラグインを読み込み、`cmds.uvPathCutCtx` が在ること。GUI でリロードしてクラスの色などを変えると反映されること。

**実装**: [constants.py](../../constants.py)・[reloader.py](../../reloader.py)・[api.py](../../api.py)・[plug-ins/uvPathCut.py](../../../../plug-ins/uvPathCut.py)
/ 記録 [00_skeleton.md](../00_skeleton.md)

## 手順 2: 設定の定義表と保存

**ゴール**: 設定 (拾うもの・自動カットなど) を 1 つの表で定義し、正規化・保存・コマンドのフラグ・ウィンドウの部品をすべて表から作る。

**作るもの**: `core/settings.py` (`Setting` の表 `DEFINITIONS`・`normalize`・`Settings`)、`scene/prefs.py` (`OptionVarStorage`)

**方法**

- `Setting(key, kind, default, short_flag, label, choices, minimum, maximum, description, section, ...)`。
  種類は BOOL / CHOICE / FLOAT / COLOR
- `normalize(key, value)`: 文字列・番号・真偽値などを型に直し、範囲外は端に寄せる。直せなければ `SettingsError`
- `Settings(storage)`: `value` / `set` / `reset(keys)` / `addListener`。変えたら保存してリスナーへ知らせる
- 保存は optionVar に JSON で、**既定と違う項目だけ** (既定を後で変えたときに古い値が残らない)
- 項目を足すときは表に 1 行。フラグ (手順 3)・ウィンドウ (手順 14) も自動で出る

**確かめ方**: pytest で正規化・リセット・リスナー。mayapy で optionVar への保存と読み直し。

**実装**: [core/settings.py](../../core/settings.py)・[scene/prefs.py](../../scene/prefs.py) / 記録 [01_settings.md](../01_settings.md)

## 手順 3: ツールのコンテキスト

**ゴール**: ツールを有効 / 無効にでき、`cmds.uvPathCutCtx("名前", edit=True, pickMode="vertex")` で設定を変えられる。

**作るもの**: コンテキスト (`MPxSelectionContext`)・コンテキストのコマンド (`MPxContextCommand`)・ツールのコマンド
(決まった名前のコンテキストを作って `setToolTo`)

**方法**

- `MPxSelectionContext` を継承すると、マウスの処理を上書きしない限り、普通の選択ツールと同じに動く
- `toolOnSetup` / `toolOffCleanup` で始める / 片付ける。**基底の `toolOnSetup` を `super()` で呼ぶと SystemError** (呼ばない)
- コマンドの `appendSyntax` で設定の表からフラグを足し、`doEditFlags` / `doQueryFlags` で読む
- 問い合わせの戻り値 (`setResult`) は bool / int / float だけ。**文字列を返すと kFailure**。選択肢は番号で返す
- 色 (3 つの数) は問い合わせで返せないので、ウィンドウからは MEL の `python()` で Python の関数を呼んで受け取る

**確かめ方**: mayapy で編集と問い合わせ。GUI で `UVPathCut.tool()` -> ツールが有効になり、別のツールにすると片付くこと。

**実装**: [tool/context.py](../../tool/context.py)・[tool/command.py](../../tool/command.py) / 記録 [00_skeleton.md](../00_skeleton.md)・[01_settings.md](../01_settings.md)
