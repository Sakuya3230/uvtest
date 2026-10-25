# 段階 21: パネルの「全削除」

## 目的

ツールを使っている間に、対象のメッシュのガイドをまとめて消す。パネルのボタン「全削除」(ごみ箱のアイコン。キーは無し)。

| 操作 | 動き |
|---|---|
| 「全削除」を押す | 対象のメッシュ (ツールで扱っているもの) のガイドを、作成中のものも含めてすべて消す。確認はしない (Ctrl+Z で戻せるので。ユーザーの指定) |
| Ctrl+Z | 1 回で全部戻る (作成中のガイドも作成中のまま) |

シーンのすべてのガイド (対象でないメッシュも) を消すのは、今までどおりツール設定のウィンドウの「保存したガイド」と
api の `delete_all_guides`。

## 仕組み

```
パネル -> context._on_action(DELETE_ALL) -> guide_cleanup.delete_target_guides(対象のメッシュ)
  ガイドのあるメッシュの組を、空の GuideSet にする組を作る
  -> guide_edit.apply_many   ほかの編集と同じ 1 回の Undo (置き場所・アトリビュートの両方。前の文字列に戻す)
```

アトリビュートを消すのではなく「ガイドの無い組」を書く (ほかの編集と同じ道を通るので、Undo・表示の更新・編集の選択の
片付けが今までのまま効く)。

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [tool/guide_cleanup.py](../tool/guide_cleanup.py) | `delete_target_guides(targets)`・シーン全体の削除の確認のダイアログを `_confirmed` にまとめた |
| [tool/actions.py](../tool/actions.py) / [tool/context.py](../tool/context.py) / [ui/icons.py](../ui/icons.py) | ボタン「全削除」・ごみ箱のアイコン |
| [reloader.py](../reloader.py) | `guide_cleanup` が `guide_edit` を使うので後ろへ (`tool_settings_window` も) |

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()
# ガイドを何本か描く -> 「全削除」 -> 全部消える -> Ctrl+Z で全部戻る
```

mayapy (2027・2022) で、作成中を含む 4 本が消え、Undo で 4 本と作成中のガイドが戻り、ガイドの無いメッシュだけなら
何もしないことを確かめた。
