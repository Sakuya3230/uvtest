# 段階 26: テストを残す

## 目的

ここまでは段階ごとに使い捨てのスクリプトで確かめてきた。SeamGuide を取り入れてガイドの持ち方を変える前に、
今動いているもの (ガイドの編集・対称の相手・保存・Undo・カット・索引など) を壊していないかを、いつでも確かめられるようにする。

## 実行

```
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest scripts/tests/UVSeamTool                              # 決まりの検査 (Maya・numpy 不要)
"C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe" scripts\tests\UVSeamTool\mayapy\run_all.py          # core と Maya の流れ
"C:\Program Files\Autodesk\Maya2022\bin\mayapy.exe" scripts\tests\UVSeamTool\mayapy\run_all.py          # 2022 でも
```

Anaconda の numpy が壊れていて pytest では numpy を使えないので、numpy・scipy を使うものは mayapy で実行する
(`mayapy/support.py` が `scripts/site-packages/<版>` を sys.path に足す)。

## 中身

| ファイル | 確かめること |
|---|---|
| [tests/UVSeamTool/test_dependencies.py](../../tests/UVSeamTool/test_dependencies.py) (pytest) | 依存の向き (core / ui / utils / compat)・Qt と numpy / scipy は compat だけ・ほかのパッケージを使わない・reloader.MODULES の漏れと順・1 ファイル 300 行まで・Python 3.7 で読める |
| [tests/UVSeamTool/mayapy/test_core.py](../../tests/UVSeamTool/mayapy/test_core.py) | numpy の格子で: 最短パス・まっすぐさ (曲がり 1 回・長さは同じ・逆向きも同じ)・点の追加 / 挿入 / 削除・閉じたガイド・点のドラッグ・ガイドの組の流れ・選び方の修飾キー・シーム・JSON (読めない形は ValueError)・対応表・相手の作り直し (作る / 相手の編集で元を / 消す / 面の上は作らない)・ループ・パネルの折り返し |
| [tests/UVSeamTool/mayapy/test_scene.py](../../tests/UVSeamTool/mayapy/test_scene.py) | Maya standalone の球で: 保存と読み直し・点ごとの Undo・トポロジーが変わると使わずに残し Undo で戻る・対称の相手・自動のカットと Undo・相手にもカット・全削除と Undo・抜けるときの選択・レイの索引をカットのあとに捨てる・api の cut_path |
| [tests/UVSeamTool/mayapy/run_all.py](../../tests/UVSeamTool/mayapy/run_all.py) | 上の 2 つを別のプロセスで |

- 設定は `settings.install(Settings())` で保存しない設定に差し替える (ユーザーの設定のファイルを書き換えない)。
  そのために [core/settings/settings.py](../core/settings/settings.py) に `install` を足した
- ガイドの置き場所はテストごとに新しくする (`guide_store._STORE`)
- コンテキスト・ビュー・Qt のパネルは standalone では作れないので、GUI で確かめる (サブツールが呼ぶのと同じ関数をテストする)

## 足すとき

- core の決まり: `test_core.py` に `test_*` 関数を足す (格子は `support.grid(n)`)
- Maya の流れ: `test_scene.py` に `test_*` 関数を足し、最初に `new_scene(設定=値)` を呼ぶ
