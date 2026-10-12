# 段階 0: パッケージの骨組みとプラグインの入口

[目次](README.md)

## 目的

- ツールの中身を `scripts/UVPathCut` パッケージに置き、プラグインは登録だけにする
- パッケージをリロードすれば、プラグインを読み直さずに新しいコードでツールを作れるようにする
- このツールにするコマンド (`uvPathCutTool`) を用意する。ツールはまだ何もしない
  (有効 / 無効になったことをスクリプトエディタに出すだけ)

## 追加・変更した箇所

| 場所 | 内容 |
|---|---|
| [plug-ins/uvPathCut.py](../../../plug-ins/uvPathCut.py) | 登録だけのプラグイン。creator がパッケージのクラスを毎回引く |
| [plug-ins/uvPathCut.py:50](../../../plug-ins/uvPathCut.py#L50) `initializePlugin` | `uvPathCutCtx` (コンテキストのコマンド) と `uvPathCutTool` を登録 |
| [plug-ins/uvPathCut.py:59](../../../plug-ins/uvPathCut.py#L59) `uninitializePlugin` | ツールのコンテキストを消してから登録を外す |
| [constants.py](../constants.py) | プラグインとパッケージが共有する名前 (プラグイン名・コマンド名・コンテキスト名) |
| [log.py](../log.py) | `info` (print) / `warning` (Maya の警告)。頭に「UV パスカット:」 |
| [tool/context.py:32](../tool/context.py#L32) `UVPathCutContext` | ツール本体 (MPxSelectionContext)。有効 / 無効をログに出す |
| [tool/context.py:49](../tool/context.py#L49) `UVPathCutContextCommand` | `makeObj` でコンテキストを作る |
| [tool/context.py:62](../tool/context.py#L62) `ToolCommand` | 決まった名前のコンテキストが無ければ作り、`setToolTo` |
| [tool/context.py:76](../tool/context.py#L76) `delete_tool_context` | このツールのコンテキストを消す (リロード・アンロードの前) |
| [api.py](../api.py) | `tool()` / `load_plugin()` / `plugin_path()` / `reload_modules()` |
| [reloader.py:21](../reloader.py#L21) `MODULES` / `MAYA_MODULES` | 依存順のモジュールの一覧 (Maya 不要 / Maya が要る) |
| [reloader.py](../reloader.py) `reload` / `reload_modules` | 自分を読み直して返す / コンテキストを消してから、依存順にリロード |
| [core/](../core/__init__.py) / [scene/](../scene/__init__.py) / [tool/](../tool/__init__.py) | 層の入れ物 (docstring に依存してよいもの) |
| [tests/UVPathCut/test_dependencies.py](../../tests/UVPathCut/test_dependencies.py) | 依存の向き・`MODULES` の漏れ (pytest) |
| [tests/UVPathCut/mayapy/test_plugin.py](../../tests/UVPathCut/mayapy/test_plugin.py) | 読み込み・リロード・アンロード (mayapy) |
| 旧版 | [plug-ins/old/uvPathCut_v1.py](../../../plug-ins/old/uvPathCut_v1.py) と [tests/UVPathCut/old/](../../tests/UVPathCut/old/test_uv_path_cut_v1.py) に移した (コマンド名が同じなので同時に読み込めない) |

## 仕組み

### プラグインの読み込みと登録

1. `cmds.loadPlugin("uvPathCut")` で、Maya はプラグインのファイルを **名前の無い名前空間** で実行する
   (`sys.modules` には入らない)
2. `maya_useNewAPI()` があると、API 2.0 (`maya.api.OpenMaya`) のプラグインとして扱う
3. `initializePlugin(plugin)` が呼ばれる。`MFnPlugin` で次を登録する
   - `registerContextCommand(名前, creator)`: コンテキストを作るコマンド
   - `registerCommand(名前, creator)`: 普通のコマンド
4. `cmds.unloadPlugin` で `uninitializePlugin` が呼ばれ、登録を外す

### creator がクラスを毎回引く理由

creator は「コマンドが呼ばれるたびに、そのインスタンスを作る関数」。
クラスそのもの (`UVPathCutContextCommand`) を渡すと、登録した時点のクラスが使われ続け、
パッケージをリロードしても古いコードが動く。そこで creator の中で

```python
importlib.import_module("UVPathCut.tool.context").UVPathCutContextCommand()
```

と **呼ばれるたびに** モジュールを引く。リロードしたあとに作るものは新しいクラスになる
(MayaKit の [mayakit_attribute.py](../../../plug-ins/mayakit_attribute.py) と同じ方式)。

### ツール (コンテキスト) ができるまで

```
UVPathCut.tool()
  -> load_plugin()                       プラグインが読み込まれていなければ読む
  -> cmds.uvPathCutTool()                ToolCommand.doIt
       -> cmds.uvPathCutCtx("uvPathCutContext")    無ければ作る
            -> UVPathCutContextCommand.makeObj()   UVPathCutContext を作って返す
       -> cmds.setToolTo("uvPathCutContext")       使い始める
            -> UVPathCutContext.toolOnSetup()      「ツールを有効にしました」
```

- 決まった名前のコンテキストを使い回すので、何度 `tool()` を呼んでもツールは 1 つ
- `MPxSelectionContext` は選択ツールの機能を持つ。マウスの処理を上書きしていないので、
  今は普通の選択ツールと同じに動く

### リロード

```python
import UVPathCut.reloader as r; r.reload().reload_modules()
```

1. **`r.reload()`** が `reloader` 自身を読み直して、**読み直したモジュールを返す**。
   `import UVPathCut.reloader as r` は読み込み済みの古いモジュールを返すので、そのまま
   `reload_modules()` を呼ぶと、`MODULES` に足した新しいモジュールがリロードされない
   (段階 3 で、リロードのあとに古い `scene.mesh` が残る不具合が出た)。返ってきた新しい
   `reloader` の `reload_modules()` を呼ぶので、いつもファイルにある新しい一覧が使われる
   (`AttributeInspector` の reloader と同じ形)
2. `reload_modules()` がこのツールのコンテキストを消す (`delete_tool_context`。使っていたら選択ツールに戻してから)
3. `MODULES` → `MAYA_MODULES` の順にリロードする (読み込まれていなければ import)
4. 一覧に無いのに読み込まれている UVPathCut のモジュールがあれば、スクリプトエディタに知らせる
   (読み直していないので、古いコードのまま)
5. 読み込み済みのプラグインに、`constants.PLUGIN_COMMANDS` / `PLUGIN_NODES` がそろっているかを確かめ、
   足りなければプラグインを読み直す (`api.ensure_plugin_current`)。コマンド・ノードの **登録** は
   プラグインを読み込んだとき (`initializePlugin`) にしか行われないので、モジュールのリロードでは
   増えない (段階 8 で `uvPathCutEdit` を足したとき「Cannot find procedure」になった)。
   プラグインのコマンドが Undo のキューに残っていると外せないので、先に Undo の履歴を消す (`flushUndo`)

`UVPathCut.reload_modules()` (api) も同じこと (`reloader.reload().reload_modules()`) をする。

コンテキストを消すのは、**作ったときのクラスのインスタンスのまま残る** ため。
消して作り直せば新しいクラスになる。プラグインは読み直さなくてよい。

## 落とし穴

- API 2.0 の `MPxSelectionContext` で `super().toolOnSetup(event)` を呼ぶと `SystemError`
  (旧版で確認)。基底の `toolOnSetup` / `toolOffCleanup` は呼ばない
- クラスでは **引数なしの `super()`** を使う。`super(クラス, self)` は、リロードのあとに
  古いインスタンスへイベントが届くと、名前が新しいクラスを指して `TypeError` になる
- mayapy (standalone) ではコンテキストを作れない (コンテキストのコマンドが False を返す)。
  ツールの動きは GUI で確かめる
- Windows はファイル名の大文字・小文字を区別しないので、`tests/uvPathCut` と `tests/UVPathCut`
  は同じフォルダ。名前を変えるときは一度別の名前を経由する
- mayapy は起動用のバッチを通らないので `MAYA_PLUG_IN_PATH` にプラグインのフォルダが無い。
  `load_plugin` は名前で読めなければ、パッケージの場所からのフルパスで読む

## 試し方

```python
import UVPathCut
UVPathCut.tool()          # スクリプトエディタに「UV パスカット: ツールを有効にしました」
# 移動ツール (W) などに替えると「ツールを無効にしました」

import UVPathCut.reloader as r; r.reload().reload_modules()   # ツールのコンテキストが消える
UVPathCut.tool()          # 新しいクラスで作り直される
```
