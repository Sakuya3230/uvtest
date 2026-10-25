# 段階 0: 仕様と決めごと

UVPathCut を、自分で読んで保守できる形に作り直すための仕様。後で SeamGuide を取り入れても
構造が複雑にならないよう、ガイドを中心にして最初に骨組みを決める。

旧版は触らずに残す (UVPathCut・SeamGuide とは別のパッケージとして並べて作る)。

## 1. 名前

すべて `UVSeamTool` から作る。シーンや設定ファイルに残るので、途中で変えない。

| もの | 名前 |
|---|---|
| パッケージ | `scripts/UVSeamTool/` |
| プラグイン | `plug-ins/uvSeamTool.py` |
| コンテキストのコマンド | `uvSeamToolCtx` |
| ツール設定のウィンドウ (MEL の入り口) | `uvSeamToolProperties` / `uvSeamToolValues` |
| 設定のファイル | `constants.SETTINGS_PATH` (後述) |
| ガイドの保存 | シェイプのアトリビュート `uvSeamToolGuides` (`constants.GUIDE_ATTRIBUTE`) |

## 2. 環境

| 項目 | 決めたこと |
|---|---|
| Maya | 2022〜2027 (Python 3.7〜3.13)。2020 以前は扱わない |
| Qt | PySide2 5.15 (2022〜2024) / PySide6 (2025〜) |
| numpy / scipy | **必須**。pip で入れた環境 (`maya20XX.bat` が `scripts/site-packages/<版>` を PYTHONPATH に足す) で使う。Python 版の代わり (フォールバック) は作らない |
| 足りないとき | 起動の時点で止めて、何が足りないかと入れ方を知らせる |
| 色の管理 | 3D の描画はカラーマネジメントを考えない (必要になったら足す) |

手元で確かめたこと (2026-10-24):

| 版 | Python | Qt | Maya 本体の numpy | pip の numpy / scipy |
|---|---|---|---|---|
| 2022 | 3.7.7 | PySide2 5.15.2 | なし | 1.21.6 / 1.7.3 |
| 2025 | 3.11.4 | PySide6 6.5.3 | 1.24.4 | 2.1.3 / 1.14.1 |
| 2027 | 3.13.9 | PySide6 6.8.3 | 2.3.5 | 2.4.4 / 1.17.1 |

numpy は 1.21〜2.4、scipy は 1.7〜1.17 の幅がある。**テストは必ず 2022 と 2027 の両方で回す**。
numpy 2.0 で消えた書き方 (`np.float` など) は使わない。

### 版の違いは compat に閉じ込める

```
compat/
    qt.py      PySide6 / PySide2 の差 (QAction の場所・exec と exec_・イベントの位置・wrapInstance)
    accel.py   numpy / scipy を読み込む。読み込めなければ理由を返す (起動の確認に使う)
    maya.py    Maya の版による API の差 (必要になったときだけ作る)
```

- PySide・shiboken・numpy・scipy を import してよいのは compat だけ。ほかは compat から受け取る
- 版を見る `if` は compat の中だけに書く

## 3. コードのルール (読みやすさを優先する)

- Python 3.7 で動く書き方。dataclass・型ヒント (`from __future__ import annotations`)・f-string を使う。
  walrus (`:=`)・`match` は使わない
- クラスでは引数なしの `super()` (リロード後の TypeError を避ける)
- **mixin を使わない**。機能は別のクラスにして、持つ形にする
- 1 ファイル 300 行まで。モジュールの先頭に「何を受け取り、何を返すか」を書く
- 名前は略さない。コメントは「なぜ」を書く
- 今要らない機能のための仕組みを先に作らない (足せる形だけにしておく)
- 名前の付け方・クラスの中の並び順・変数の読み書きは [coding_rules.md](coding_rules.md)

## 4. 骨組み

### パッケージの構成

```
UVSeamTool/
    __init__.py        from .api import *
    api.py             tool()・add_shelf_button() などの入り口
    constants.py       名前・保存先 (プラグインと、すべてのフォルダが使う)
    reloader.py
    compat/            版の違い (qt.py・accel.py)
    utils/             Maya の cmds / API を包む・環境 (設定のファイルのパスなど) を解決する。ツールの判断を持たない
        log.py
        node.py            名前 <-> MObject / MDagPath・フルパス・名前だけ・トランスフォームとシェイプ
        mesh.py            Mesh: メッシュのトランスフォーム 1 つ (位置・エッジを numpy で読む)
        uv_editor.py       polyMapCut / polyMapSew
        undo.py            Undo のコマンドの仕組み
        selection.py       選択からメッシュ (Mesh) を取る
    core/              機能の核。機能ごとのフォルダ
        guide/             guide_point.py・guide_segment.py・guide.py・guide_set.py・editing.py
        path/              mesh_graph.py・shortest_path.py
        seam/              seam.py (ガイド -> エッジの列)
        settings/          setting.py・definitions.py・settings.py・json_storage.py
    ui/                Qt (ビューの上のパネル・部品)
    tool/              コンテキスト・サブツール・マニピュレータ・キー・ツール設定のウィンドウ
```

(ファイル名は案。作る段階で決める。)

旧 UVPathCut の `scene/` は作らない。`scene/` には「Maya を触る所」と「ツールの判断」(どのセッションを使うか など) が
混ざっていて分かりにくかったので、Maya を触る所は utils、ツールの判断は core に分ける。

### 依存の向き

```
tool -> (ui, core) -> utils -> compat
constants はどこからでも使える (constants 自身はパッケージの中のものを import しない)
```

| フォルダ | import してよいもの | してはいけないもの |
|---|---|---|
| constants | 標準ライブラリ | パッケージの中のすべて |
| compat | 標準ライブラリ・PySide・shiboken・numpy・scipy・maya | utils・core・ui・tool |
| utils | maya・compat・constants | core・ui・tool |
| core | utils・compat・constants | maya・Qt・ui・tool |
| ui | core・utils・compat (qt)・constants | maya・tool |
| tool | すべて | - |

依存のテスト (AST) で検査する。core が numpy を使うので、core のテストも mayapy で回す (Anaconda の numpy が壊れているため)。

### utils の約束

- **メッシュはトランスフォームで指す** (シェイプは `Mesh` の中で、使うときに引く)。名前ではなく
  MObjectHandle / MDagPath で持つので、名前を変えられても同じメッシュを指す。cmds にはフルパスを渡す
- **core に Maya の型 (MObject・MFnMesh・MDagPath など) を渡さない**。core が受け取るのは名前・番号・数・
  numpy の配列だけ。`node.py` の変換 (MObject / MDagPath) は utils と tool の中で使う

```python
mesh  = Mesh.fromName("pSphere1")                       # utils (トランスフォームの名前。シェイプの名前でもよい)
graph = MeshGraph(mesh.points(), mesh.edgeVertices())   # core は numpy の配列だけを受け取る
```

こうすると core は Maya の型を知らずに済み、テストでは作った配列を渡すだけで core を確かめられる。

### コンテキストは振り分けるだけ

コンテキストはマウスとキーを、今のサブツールに渡すだけにする。
今の UVPathCut の `doPress` の中のモードの分岐 (`_wants_ring` / `_wants_selection` / `_wants_click`) を作らない。

```python
class SubTool:
    def press(self, event): ...
    def drag(self, event): ...
    def release(self, event): ...
    def hover(self, position): ...
    def draw(self, draw_list): ...
    def actions(self): ...   # この道具で効く操作 (ボタン・キー)
```

最初のサブツール: **ガイドを作る (最短パス)** / **ガイドを編集する** / **エッジを選ぶ**。
SeamGuide の道具 (リング・フリーハンド・ペイント…) は、後でクラスを足すだけにする。

### ガイドの持ち方

```python
@dataclass(frozen=True)
class GuidePoint:
    vertex: int                  # 今は頂点だけ。後で表面の上の自由な点・ほかのガイドに乗る点を足す

@dataclass(frozen=True)
class GuideSegment:
    mode: str = "shortest"       # 作り方。後で "curve" / "straight" / "fixed" などを足す
    vertices: tuple = ()         # 求めた頂点の列 (作り直すまで使い回す)

@dataclass(frozen=True)
class Guide:
    id: int                      # 対称の相手・つなぎ線はこれで指す
    points: tuple                # GuidePoint の列
    segments: tuple              # 点の間ごと (開いた線は len(points) - 1 本)
    closed: bool = False
```

どれも値だけの入れ物なので、[coding_rules.md](coding_rules.md) の例外どおり frozen の dataclass にする
(変えられない。編集の関数が新しい値を作る。そのため列は list ではなく tuple)。

- 区間は **作り方 -> 求める関数の表** で求める (`SOLVERS = {"shortest": solve_shortest}`)
- ガイドは 1 つのメッシュに属する (メッシュをまたがない)。ガイドの組はメッシュごと
- 点は頂点だけ (エッジを拾う機能はやめる)

### ガイドと UV を分ける

```
ガイド --(seam_of)--> エッジの列 --(cut / sew)--> UV
選んだエッジ -----------------------^
```

- カット / 縫合の関数はエッジの列だけを受け取る (ガイドのことは知らない)
- ガイドは「カット済み」などの状態を持たない。カットしたあとにガイドを編集しても、UV は変わらない
  (もう一度当てるかはユーザーが決める)
- カット済み / 縫合済みの見え方は、メッシュの実際の UV の境界から求める
- 当てる対象: **作成中は今のガイド、編集では選んでいるガイド (複数可)**

### 編集と Undo

- 編集はどれも core の関数 (ガイド -> 新しいガイド): 端に点を足す / 点を動かす (前後の 2 区間を求め直す) /
  点を挿入する (区間を 2 本に分ける) / 点を消す (前後の 2 区間を 1 本にする)
- Undo は **そのメッシュのガイドの組の、前と後を丸ごと持つコマンド 1 種類**。カット / 縫合は同じ Undo の中で
  `polyMapCut` / `polyMapSew` を呼ぶ

## 5. 設定

- 定義表 (キー・型・既定値・範囲・表示名) から、保存・コマンドのフラグ・ツール設定のウィンドウを作る (UVPathCut と同じ)
- **保存は JSON のファイル** (optionVar は Maya の版ごとの prefs に入り、版をまたいで共有できないため)
  - 書き出し先は `constants.SETTINGS_PATH`。今はユーザーの一時フォルダの `UVSeamTool/settings.json`
    (一時フォルダは OS の掃除で消えることがある。後で任意の場所に変える)
  - 既定と違う値だけを書く。形式の名前と版 (`"format": "UVSeamTool.settings", "version": 1`) を入れる
  - 知らないキー・直せない値は飛ばす (新しい版の Maya で足した項目を、古い版で読んでも壊れない)
  - 一時ファイルに書いてから入れ替える (書いている途中で落ちても壊れない)

## 6. 画面

| もの | 作り方 |
|---|---|
| 3D の描画 (面・点・ガイド・プレビュー) | マニピュレータの `drawUI` + `MUIDrawManager`。カラーマネジメントは考えない |
| ボタン (モード・カット / 縫合・クリアなど) | **Qt のパネル**。ビューに付いて動く、枠なしの Tool ウィンドウ (ViewPanelLesson の段階 2 以降と同じ。ネイティブの子ウィンドウにしない) |
| ツール設定のウィンドウ | **MEL は入り口だけ** (`uvSeamToolProperties` / `uvSeamToolValues`)。中身は `maya.cmds` で作る (ViewPanelLesson の段階 7c と同じ) |

ViewPanelLesson のコードには依存しない (必要な所を、読みやすく書き直して持ってくる)。

## 7. 機能の一覧

★ = 最初の縦の 1 本に入るもの。

### A. 土台

| # | 機能 | |
|---|---|---|
| U01 | プラグインの登録 (登録だけ)・起動 `UVSeamTool.tool()` | ★ |
| U02 | numpy / scipy の確認 (無ければ止めて知らせる) | ★ |
| U03 | 選んだメッシュを対象にする | ★ |
| U04 | 開発中のリロード | ★ |
| U05 | ログ | ★ |
| U06 | シェルフのボタン・アイコン | |

### B. ガイドを作る (最短パス)

| # | 機能 | |
|---|---|---|
| U10 | メッシュのモデルとグラフ | ★ |
| U11 | マウスの下の頂点を拾う | ★ |
| U12 | 最短パス (scipy の dijkstra) | ★ |
| U13 | まっすぐさ (曲がりの少ないパスを選ぶ重み) | ★ (段階 24) |
| U14 | クリックで点を足す (1 回目が始点、次から端に足す)。ガイドを終える操作 | ★ |
| U15 | プレビュー (始点から今の頂点まで) の描画 | ★ |
| U16 | 自動 (点を足すたびに、足した区間をカット / 縫合する) | ★ (段階 18。作成のモードだけ) |

### C. ガイドを編集する

| # | 機能 |
|---|---|
| U20 | ガイドを選ぶ (複数可) |
| U21 | 点を選ぶ (Shift・矩形で複数) |
| U22 | 点を動かす (頂点に吸い付く) |
| U23 | 線の上をクリックで点を挿入する |
| U24 | 点を消す |
| U25 | ガイドを消す |

### D. 当てる

| # | 機能 | |
|---|---|---|
| U30 | ガイド -> エッジの列 (`seam_of`) | ★ |
| U31 | カット / 縫合 (作成中は今のガイド、編集では選んだガイド) を 1 回の Undo で | ★ |
| U32 | カット済み / 縫合済みの見え方を UV の境界から求める | ★ (段階 13) |

### E. エッジを選ぶ

| # | 機能 |
|---|---|
| U40 | クリックでエッジ (Shift / Ctrl は Maya と同じ) |
| U41 | ダブルクリックでループ |
| U42 | 矩形 (表向きの面のエッジ) |
| U43 | ループのプレビュー |
| U44 | 選んだエッジをカット / 縫合 |

### F. 操作の入り口

| # | 機能 |
|---|---|
| U50 | 設定の定義表と JSON の保存 |
| U51 | コンテキストのコマンドのフラグ |
| U52 | ツール設定のウィンドウ (cmds)。保存したガイドの一覧・選んだメッシュ / すべての削除のボタンも (中身は api の `list_guides` / `delete_guides` / `delete_all_guides`) |
| U53 | ビューの上の Qt のパネル (ボタン) |
| U54 | キー |
| U55 | ヘルプ行 |

### G. 全体にかかるもの (後で足す)

| # | 機能 |
|---|---|
| U60 | ガイドの保存 (方法は実装するときに相談) |
| U61 | 複数のメッシュ |
| U62 | ツールを使っている間に選んだメッシュを足す |
| U63 | 対称 |
| U64 | 外部の変更 (位置・トポロジー・名前) の検知 |
| U65 | 扱えないメッシュ (ロック・インスタンス・UV なし) |

### 入れないもの

- 輪切りのモード (SeamGuide を取り入れるときに一緒に考える)
- エッジを拾う (点は頂点だけ)
- numpy / scipy が無いときの Python 版

### SeamGuide から後で取り入れるもの (足せる形にだけしておく)

リング・フリーハンド・ライン・カーブ・ペイント・つなぎ線・境界をガイドに (サブツールを足す) /
区間の作り方 曲線・直線・谷・固定 (`SOLVERS` に足す) / ほかのガイドに乗る点 (`GuidePoint` に足す) /
閉じたガイドのホイール / 伸ばす・つなぐ・切り離す (core の編集の関数を足す)

## 8. 最初の縦の 1 本

**UI なしで、ガイドを作る -> 最短パスで区間を求める -> カットする** (U02・U10・U12・U30・U31 の core と scene)。
mayapy で、球に 3 点のガイドを作ってカットし、UV の境界になったエッジを確かめる。
そのあとで、コンテキスト (U01・U03・U11・U14・U15) をこの核を呼ぶだけの薄い皮として足す。

## 9. 未定 (その段階で相談する)

- 作成と編集の切り替え方
- 自動 (U16) を残すか、どう当てるか → 段階 18 で決めた (点を足すたびに当てる・編集のモードでは当てない)

決まったこと:

- ガイドの保存 (U60): シェイプの文字列のアトリビュート `uvSeamToolGuides` に JSON・編集のたびに書く・
  トポロジーが違えば使わずに残す (2026-10-24。[06_save_guides.md](06_save_guides.md))

- ガイドを終える操作: **Enter で確定** (カットはしない。カット / 縫合は別の操作)。Esc で捨てる・Delete で最後の点を消す
  (2026-10-24。[03_guide_set_undo.md](03_guide_set_undo.md))
- Undo: **点ごと** (点を足す・消す・確定・捨てるが、どれも 1 回の Ctrl+Z)
- 確定せずに編集のモードへ替えた・ツールを抜けたとき: **作成中のガイドを確定する** (Enter と同じ。点が 1 つなら捨てる。
  2026-10-24。`CreateTool.deactivate`)
