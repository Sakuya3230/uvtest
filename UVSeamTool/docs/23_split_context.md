# 段階 23: context.py を分ける

## 目的

`tool/context.py` が 444 行になった (決まりは 300 行まで)。役目ごとにクラスを分ける。

| モジュール | クラス | 役目 |
|---|---|---|
| [tool/context.py](../tool/context.py) (240 行) | `UVSeamToolContext` | ツールの有効 / 無効・マウスとキーを今のサブツールへ渡す・モードの切り替え・描画 |
| [tool/target_watch.py](../tool/target_watch.py) | `TargetWatch` | 対象のメッシュの見張り: 外からの変更 (読み直す・消されたら外す)・選んだメッシュを足す・エッジの選択モードを保つ |
| [tool/tool_actions.py](../tool/tool_actions.py) | `ToolActions` | パネルのボタン・キー・マーキングメニューの操作を当てる・パネルとメニューの出し入れ・見た目 (`states`)・設定の変更 |

## つながり

```
UVSeamToolContext
  _watch   = TargetWatch(targets, on_changed)      対象が変わったら on_changed -> 各サブツールの targetChanged
  _actions = ToolActions(self)                     context の mode() / setMode() / subTool() / subTools() / targets() を使う
  setMode -> _actions.sync() (パネルの見た目)
```

- `ToolActions` はツールの公開メソッドだけを使う (context の中身に触らない)
- 設定の変更は `ToolActions` が聞く (install から release の間)。パネルの見た目・パネルの出し入れ・ツール設定のウィンドウの値・
  対称 / 自動のログ
- 設定を切り替えるだけの操作 (対称・自動・パネルを表示) は表 `_TOGGLE_SETTINGS` にまとめた

## 試し方

ツールの操作はすべて前と同じ (段階 1〜22 の試し方がそのまま使える)。
