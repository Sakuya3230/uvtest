# 段階 6: ガイドの保存

## 目的

ガイドをシーンに保存し、Maya を閉じても・リロードしても残るようにする。

## 決めたこと (ユーザーの選択)

| 問い | 決めたこと |
|---|---|
| 保存先 | メッシュの **シェイプ** の文字列のアトリビュート `uvSeamToolGuides` (`constants.GUIDE_ATTRIBUTE`)。複製・書き出しでも一緒に付いていく |
| トポロジーが変わっていたら | **使わずに残す**。警告して、そのメッシュではガイドなしとして扱う。アトリビュートは書き換えないので、Undo でトポロジーを戻せばまた使える。新しいガイドを作ると上書きする |
| いつ書くか | **編集のたび** (ガイドの組が変わるたび。Undo / Redo でも書き戻す) |

## 保存の形

```json
{"format": "UVSeamTool.guides", "version": 1,
 "topology": {"vertices": 382, "edges": 780, "hash": "1a2b3c4d5e6f7a8b"},
 "active_id": null,
 "guides": [{"id": 0, "closed": false, "points": [0, 105, 210],
             "segments": [{"mode": "shortest", "vertices": [0, 1, 2, 3, 4, 5, 25, 45, 65, 85, 105]},
                          {"mode": "shortest", "vertices": [105, 106, 107, 108, 109, 110, 130, 150, 170, 190, 210]}]}]}
```

- `topology` は頂点の数・エッジの数・エッジの配列のハッシュ (sha1 の先頭 16 文字)。位置は含めないので、頂点を動かしただけなら同じ
- 区間の頂点の列 (求めたもの) も保存する。後で足す作り方 (固定など) は、求め直せない形を持つため

## 流れ

```
ツールを有効にする -> TargetMesh(mesh)
  -> topology_of(頂点の数, エッジ) (core)                          トポロジーの目印
  -> guide_storage.load(mesh, topology) (tool)
       guide_attribute.read_text (utils) -> guide_json.loads (core) -> 目印が違えば空の組 (警告)
  -> guide_store に入れる
編集 -> guide_edit.apply(target, 新しい組)
  -> undo.run(redo, undo)                                         どちらも _set(target, 組)
       guide_store.setGuideSet + guide_storage.save
                                   -> guide_json.dumps (core) -> guide_attribute.write_text (utils。MPlug で書く)
```

## 追加・変更したもの

| ファイル | 中身 |
|---|---|
| [core/path/topology.py](../core/path/topology.py) | `topology_of(頂点の数, エッジ)` |
| [core/guide/guide_json.py](../core/guide/guide_json.py) | `dumps(組, topology)` / `loads(文字列)` -> (組, topology)。形・版が違えば ValueError |
| [utils/guide_attribute.py](../utils/guide_attribute.py) | `read_text(mesh)` / `write_text(mesh, 文字列)` (無ければアトリビュートを作る) |
| [tool/guide_storage.py](../tool/guide_storage.py) | `load(mesh, topology)` / `save(mesh, topology, 組)`。読めない・トポロジーが違う・書けないときの警告 |
| [tool/target_mesh.py](../tool/target_mesh.py) | 作るときにトポロジーの目印を作り、保存したガイドを読んで guide_store に入れる。`topology()` |
| [tool/guide_edit.py](../tool/guide_edit.py) | `apply(target, 組)`: 置き場所とアトリビュートの両方を変える (呼ぶ側は key ではなく TargetMesh を渡す) |
| [constants.py](../constants.py) | `GUIDE_ATTRIBUTE` |
| [api.py](../api.py) | `cut_guides` / `sew_guides` は TargetMesh で保存したガイドを読んで当てる (ツールを使っていなくても) |

## 仕組み

- **アトリビュートが正、guide_store は写し**: 描画のたびに JSON を読むのは遅いので、ツールを有効にしたときに
  1 回読んで guide_store に入れる。変えるときは両方を同じ Undo のコマンドの中で変える
- **API (MPlug) で書く**: 書くのは自分の Undo のコマンド (`utils.undo`) の redo / undo の中。`cmds.setAttr` を使うと、
  Undo の列に別の 1 回として積まれてしまう。アトリビュートを作るのも API (`MFnDependencyNode.addAttribute`)
- **リロードしても残る**: リロードで guide_store は空になるが、次にツールを有効にしたときにアトリビュートから読む

## 落とし穴

- ロックされたノードには書けない (警告するだけ。ガイドは guide_store には残る)
- アトリビュートを作るのは Undo されない (Undo で最初の編集の前に戻しても、空の組が書かれたアトリビュートは残る)
- トポロジーが違って使わなかったガイドは、新しいガイドを作った時点で上書きされて消える
- 同じシェイプのインスタンスは、ガイドを共有する (シェイプが 1 つなので)

## 試し方

```python
import UVSeamTool.reloader as r; r.reload().reload_modules()
import maya.cmds as cmds, UVSeamTool
cmds.polySphere(); UVSeamTool.tool()
# ガイドを作る -> 別のツール (W) -> もう一度 UVSeamTool.tool() -> ガイドが残っている
# リロードしても残る / シーンを保存して開き直しても残る
print(cmds.getAttr("pSphereShape1.uvSeamToolGuides"))   # 中身を見る
```

mayapy (2022 / 2027) で、編集のたびの書き込み・Undo / Redo の書き戻し・シーンを保存して開き直す・
スムーズでトポロジーを変えると使わずに残すこと、を確かめた。

## 追加: 保存したガイドの一覧と削除

受け渡しのときなどに、シェイプに残ったアトリビュートを消せるようにした。ボタンは設定の段階でツール設定のウィンドウに置く予定。

```python
UVSeamTool.list_guides()          # メッシュごとの [{"mesh", "guides", "usable"}]。ログにも出す
UVSeamTool.delete_guides()        # 選んでいるメッシュ (mesh_names=[...] でも)。1 回の Undo
UVSeamTool.delete_all_guides()    # シーンのすべて (GUI なら確認する。confirm=False で聞かない)。1 回の Undo
```

| ファイル | 中身 |
|---|---|
| [utils/guide_attribute.py](../utils/guide_attribute.py) | `meshes_with_guides()` (MItDag でアトリビュートを持つシェイプ。インスタンスは 1 つに)・`delete(mesh)` (`removeAttribute`) |
| [tool/guide_cleanup.py](../tool/guide_cleanup.py) | `list_guides()`・`delete_guides(meshes)` |
| [api.py](../api.py) | `list_guides` / `delete_guides` / `delete_all_guides` |

- **削除も自分の Undo のコマンドで**: 消す前の文字列とツールの中の写し (guide_store) を覚えておき、Ctrl+Z で両方を戻す。
  `cmds.deleteAttr` だとアトリビュートは戻っても写しが空のままになり、ツールを使っている最中だと描画と食い違う
- `usable` は、今のトポロジーが保存したときと同じか (違えばツールでは使われずに残っている)
- リファレンスの元のファイルにあったアトリビュートは消せない (警告して飛ばす)
- mayapy (2022 / 2027) で、一覧 (インスタンスは 1 つ)・選んだメッシュの削除・すべての削除と、それぞれの Undo / Redo を確かめた
