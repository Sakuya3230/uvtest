# 段階 7a: 設定 (色) と JSON のファイルへの保存

## 目的

描画の色を設定にし、Maya の版をまたいで同じ JSON のファイルに保存する。ツール設定のウィンドウ (7b) の土台。

最初に入れた項目は **色だけ** (ユーザーの選択。ほかは後で表に 1 行ずつ足す)。

```python
import UVSeamTool
UVSeamTool.settings().setValue("guideColor", (1, 0, 0))   # すぐ保存し、ツールを使っていればビューも描き直す
UVSeamTool.settings().value("guideColor")
UVSeamTool.settings().reset()                              # すべて既定に戻す
```

保存先は `constants.SETTINGS_PATH` (今はユーザーの一時フォルダの `UVSeamTool/settings.json`。後で任意の場所に変える)。

```json
{"format": "UVSeamTool.settings", "version": 1, "values": {"guideColor": [1.0, 0.0, 0.0]}}
```

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [core/settings/setting.py](../core/settings/setting.py) | `Setting`: 項目 1 つの定義 (キー・種類・既定・表示名・欄)。種類は今は `COLOR` だけ |
| [core/settings/definitions.py](../core/settings/definitions.py) | `DEFINITIONS`: 項目の表 (色 10 個)。`BY_KEY` |
| [core/settings/json_storage.py](../core/settings/json_storage.py) | `JsonStorage`: 読む・書く (一時ファイルに書いてから入れ替える) |
| [core/settings/settings.py](../core/settings/settings.py) | `Settings` (値・`setValue`・`reset`・リスナー)・`normalize`・`current()` (パッケージに 1 つ) |
| [tool/guide_drawing.py](../tool/guide_drawing.py) | 色の定数をやめて `color(key)` で設定から引く |
| [tool/create_tool.py](../tool/create_tool.py) / [tool/edit_tool.py](../tool/edit_tool.py) | `color("previewColor")` などに |
| [tool/context.py](../tool/context.py) | 設定が変わったら描き直す |
| [api.py](../api.py) | `settings()` |

## 仕組み

- **項目は表で持つ**: 項目を足すときは `DEFINITIONS` に 1 行足し、使う所で `settings.current().value("キー")` を引く。
  定数を import しないので、値は使うたびに引かれ、変えるとすぐ効く
- **保存するのは既定と違う値だけ**: 既定を後で変えたとき、変えていない項目は新しい既定になる
- **読むときは寛容に**: 知らないキー (別の版で足した項目)・直せない値は飛ばし、壊れたファイルは空として扱う。
  Maya の版をまたいで同じファイルを使うため
- **変わったときだけ知らせる**: `setValue` は直した値が今と同じなら何もしない (保存もしない)
- **色の直し方**: 3 つの数にして、0〜1 に収める (範囲の外は端に寄せる)

## 見送ったこと

- コンテキストのコマンドのフラグ: ツール設定のウィンドウを cmds (Python) で作るので、ウィンドウから `Settings` を直接
  変えられる。MEL から設定を変えたくなったら足す (2022 以降なら `parser` / `syntax` が使える)

## 落とし穴

- `current()` はモジュールの中に持つので、リロードすると作り直してファイルから読み直す (値はファイルにあるので消えない)
- 保存先は一時フォルダなので、OS の掃除で消えることがある (既定の値に戻るだけ)

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()
UVSeamTool.settings().setValue("guideColor", (1, 0, 0))   # 確定したガイドが赤になる
from UVSeamTool.constants import SETTINGS_PATH; print(open(SETTINGS_PATH, encoding="utf-8").read())
UVSeamTool.settings().reset()
```

mayapy で、色の範囲の補正・同じ値では知らせない・既定と違う値だけを保存・知らないキーと直せない値を飛ばす・
既定に戻す・壊れたファイルを既定として扱うこと、を確かめた。

## 変えたこと: ガイドの既定の色

確定したガイドの水色が、Maya のエッジの選択モード (段階 14) のエッジの青と見分けにくかった。一度黄緑にしたが分かりにくく、
ユーザーの指定で次のようにした。

| 設定 | 最初 | 今 |
|---|---|---|
| 確定したガイド `guideColor` | 水色 | マゼンタ (1.00, 0.30, 0.85)。前の作成中の色 |
| 作成中のガイド `activeColor` | マゼンタ | 橙 (1.00, 0.55, 0.10)。選んでいるガイドと同じ (今、手を入れているガイドが作成でも編集でも同じ色) |
| マウスの下のガイド `hoverGuideColor` | 明るい水色 | 明るいマゼンタ (1.00, 0.70, 0.95) |

保存するのは既定と違う値だけなので、自分で変えていなければ新しい既定が使われる。
