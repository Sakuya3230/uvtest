# コーディングルール

読んで分かることを優先する。ここに無いことは [00_spec.md の 3. コードのルール](00_spec.md#3-コードのルール-読みやすさを優先する) と
Python の普通の書き方 (PEP 8) に従う。

考え方: **外から呼ぶもの (公開) は camelCase、中だけで使うもの (非公開) は `_` + snake_case**。
Maya・Qt のメソッド (`doPress`・`paintEvent`・`setText`) と同じ形にそろえ、見ただけで公開か非公開かが分かるようにする。

## 1. 名前

| もの | 書き方 | 例 |
|---|---|---|
| クラス | PascalCase | `GuideSet`、`ShortestSolver` |
| クラス内の変数 (インスタンスの変数) | `self._` + snake_case (**必ず非公開**。外からはメソッドで読む / 変える) | `self._mesh_name` |
| クラス内の定数 | UPPER_SNAKE_CASE (クラスの本体に書く) | `MAX_POINTS = 1000` |
| 公開メソッド | camelCase | `addPoint()`、`activeGuide()` |
| 非公開メソッド | `_` + snake_case | `_solve_segment()` |
| スタティックメソッド | 公開は camelCase、非公開は `_` + snake_case | `isValidId()` |
| クラスメソッド | 同上。別の形から作るものは `from` + 名詞 | `fromJson()`、`fromVertices()` |
| 関数 (モジュールの) | snake_case | `shortest_path()`、`seam_of()` |
| 非公開の関数 | `_` + snake_case | `_edge_weights()` |
| 定数 (モジュールの) | UPPER_SNAKE_CASE。非公開は `_` を付ける | `SETTINGS_PATH`、`_EPSILON` |
| 引数・ローカル変数 | snake_case | `guide_id`、`start_vertex` |

補足:

- **略語**: `UV` だけは大文字のまま (`UVSeamTool`・`UVBorder`)。ほかの略語は普通の 1 語として扱う (`JsonStore`・`loadJson()`)。
  略さずに書けるものは略さない (`idx` ではなく `index`、`pt` ではなく `point`)
- **上書きするメソッドは元の名前のまま** (Maya の `doPress`・`toolOnSetup`、Qt の `paintEvent`・`eventFilter`)。この表の外
- **真偽値を返すもの**: `isClosed()` / `hasStart()` / `canCut()`。設定は `setClosed(value)`
- **Qt のシグナル**: camelCase の過去形 (`guideChanged`・`pointMoved`)
- **コールバック** (Maya の通知・リスナー・Qt のスロットのうち中で使うもの): `_on_` + 何が起きたか (`_on_selection_changed`)
- **`@property` は使わない** (`name()` / `setName()` の形にそろえる。属性に見えて処理が走るのを避ける)

## 2. モジュールとフォルダ

- **状態を持つクラスは 1 クラス 1 モジュール**。ファイル名はクラス名の snake_case (`GuideSet` -> `guide_set.py`)
- **関数だけのモジュール**は、関係する関数をまとめる (`editing.py` = ガイドの編集の関数)
- 値だけの小さな入れ物 (frozen の dataclass) も 1 つずつのモジュールにする (`guide_point.py`)
- **`__init__.py` で名前を集め直さない** (どこから来たか分からなくなり、リロードで古いものが残る)。
  import は長くなっても、どこにあるかがそのまま分かる形にする (`from ..core.guide.guide_set import GuideSet`)
- パッケージの中は相対 import。Maya・標準ライブラリは絶対 import
- フォルダごとの役割と、import してよいものは [00_spec.md の 4. 骨組み](00_spec.md#4-骨組み)
- モジュールを足したら `reloader.MODULES` に依存の順で足す (漏れと順番はテストで検査する)

## 3. 変数の読み書きはメソッドを通す

```python
class MeshTarget:
    def __init__(self, shape):
        self._shape = shape
        self._name = ""
        self._visible = True

    def shape(self):              # 読むだけ (変えるメソッドを作らない = 外から変えられない)
        return self._shape

    def name(self):
        return self._name

    def setName(self, name):      # 変えるのはここだけ。値の確かめ・通知もここに書く
        self._name = str(name)

    def isVisible(self):
        return self._visible

    def setVisible(self, visible):
        self._visible = bool(visible)
```

- 読むメソッドは名詞 (`name()`)、変えるメソッドは `set` + 名詞 (`setName()`)。真偽値は `isX()` / `setX()`
- 変えてほしくない値は、変えるメソッドを作らない
- 変えるメソッドは何も返さない (None)
- リストなどを返すときは写しを返す (`return list(self._points)`)。中身を外で書き換えられないように
- 同じクラスの中では `self._name` を直接使ってよい

### 例外: データの入れ物 (dataclass)

点・区間のような **値だけを持つ小さな入れ物** は dataclass にし、フィールドを公開の snake_case で持つ
(`point.vertex`)。そのかわり `frozen=True` で**変えられないようにする**。変えるときは core の編集の関数が新しい値を作る
(`dataclasses.replace`)。メソッドを持ち、状態が変わるクラスは上の読み書きのメソッドの形にする。

```python
@dataclass(frozen=True)
class GuidePoint:
    vertex: int
```

## 4. クラスの中の並び順

上から次の順に書く。区切りに `# -- 名前 ---` のコメントを入れる (無い区分は書かない)。

1. **クラス内の定数** (・Qt のシグナル)
2. **特殊メソッド**: `__init__` を先頭に、`__repr__`・`__eq__`・`__len__` など
3. **上書きするメソッド** (Maya・Qt・基底クラスのもの)。基底クラスごとにまとめる
4. **スタティックメソッド**
5. **クラスメソッド**
6. **公開メソッド**
7. **非公開メソッド**

同じ区分の中は、アルファベット順ではなく**意味の順**にする。読む・変えるの組 (`name()` と `setName()`) は並べる。
非公開メソッドは、それを使う公開メソッドの順に並べると追いやすい。

```python
class GuideSet:
    """メッシュ 1 つのガイドの組。"""

    MAX_GUIDES = 1000

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, mesh_name):
        self._mesh_name = mesh_name
        self._guides = []
        self._active_id = None

    def __len__(self):
        return len(self._guides)

    # -- スタティックメソッド -------------------------------------------------
    @staticmethod
    def isValidId(guide_id):
        return isinstance(guide_id, int) and guide_id >= 0

    # -- クラスメソッド -------------------------------------------------------
    @classmethod
    def fromJson(cls, data):
        guide_set = cls(data["mesh"])
        ...
        return guide_set

    # -- 公開メソッド ---------------------------------------------------------
    def meshName(self):
        return self._mesh_name

    def activeId(self):
        return self._active_id

    def setActiveId(self, guide_id):
        self._active_id = guide_id

    def addGuide(self, guide):
        guide_id = self._next_id()
        ...

    # -- 非公開メソッド -------------------------------------------------------
    def _next_id(self):
        return max((guide.id() for guide in self._guides), default=-1) + 1
```

## 5. クラスの説明と、コンストラクタの書き方

### クラスの定義のすぐ下に、どんなクラスかを書く

すべてのクラス (dataclass も) の定義のすぐ下に docstring で、**何を表す / 何をするクラスか** を書く。
1 行で足りなければ、空行のあとに持っているもの・使い方を書く。

```python
class Mesh:
    """メッシュを持つトランスフォーム 1 つ。

    トランスフォームで指し、シェイプは使うときに引く。読んだ値は numpy の配列で返す。
    """
```

### `=` の位置をタブの位置にそろえる (コンストラクタだけ)

`__init__` の中の代入は、**全体で一番長い左辺のうしろの、次のタブの位置 (4 文字ごとの列)** に `=` をそろえる
(左辺と `=` の間は 1 文字以上あける)。コンストラクタ以外の関数の中は、そろえなくてよい。空行・コメントの行をはさんでも、`__init__` の中は同じ列にそろえる。
**インスタンスの変数 (`self._...`) は最後に 1 つの塊にまとめる** (そのクラスが何を持つかを 1 か所で見られるように)。
途中の計算に使う変数は、その前の塊に書く。

```python
    def __init__(self, positions, edges):
        lengths         = np.linalg.norm(positions[edges[:, 0]] - positions[edges[:, 1]], axis=1)
        count           = len(positions)
        # 向きの無いグラフにするため、両向きの辺を入れる
        rows            = np.concatenate([edges[:, 0], edges[:, 1]])
        columns         = np.concatenate([edges[:, 1], edges[:, 0]])
        weights         = np.concatenate([lengths, lengths])

        self._positions = positions
        self._edges     = edges
        self._matrix    = sparse.csr_matrix((weights, (rows, columns)), shape=(count, count))
        self._edge_of   = {_key(a, b): index for index, (a, b) in enumerate(edges.tolist())}
```

一番長い左辺は `self._positions` (15 文字)。字下げ 8 + 15 = 23 列目の次のタブの位置 = 24 列目に `=` を置く。

### dataclass のフィールドもそろえる

フィールドの `:`・`=`・コメントの `#` を、それぞれ同じ考え方 (その前で一番長いもののうしろの、次のタブの位置) でそろえる。
`:` と `=` は前を 1 文字以上、**コメントの `#` は前を 2 文字以上** あけてから、次のタブの位置にする。

```python
@dataclass(frozen=True)
class Guide:
    """1 本のガイド (変えられない値)。"""

    id          : int
    points      : tuple = ()        # GuidePoint の列
    segments    : tuple = ()        # GuideSegment の列
    closed      : bool  = False     # 閉じた線か
```

`:` は一番長い名前 `segments` のうしろの 16 列目、`=` は一番長い型 `tuple` のうしろの 24 列目、
`#` は一番長い既定値 `False` (30 列目まで) のうしろに 2 文字あけた次のタブの位置の 36 列目。

## 6. 空行で処理のまとまりを分ける

関数・メソッドの中は、まとまりごとに空行で分ける。

- 早く返す `if` (`return` / `continue` / `raise` で抜けるもの) のあと
- コメントを付けた処理のまとまりの前
- 最後の `return` の前 (関数が 1 行・2 行だけのときは入れない)
- 空行には空白を残さない

```python
def shortest_path(graph, start, goal):
    """start から goal までの頂点の列 (両端を含む tuple)。つながっていなければ None。"""
    if start == goal:
        return (start,)

    _, predecessors = csgraph.dijkstra(graph.matrix(), indices=start, return_predecessors=True)
    if predecessors[goal] == _NO_PREDECESSOR:
        return None

    # goal から前の頂点をたどって start まで戻り、逆にする
    vertices = [goal]
    while vertices[-1] != start:
        vertices.append(int(predecessors[vertices[-1]]))

    return tuple(reversed(vertices))
```

## 7. API の型を返す関数は、型が分かる名前にする

Maya の API の型を返す関数は、名前に型を入れる (`mobject_from_name` -> MObject、`dag_path_from_name` -> MDagPath、
`mesh_shape_path` -> MDagPath)。名前の文字列を返す関数は `full_path` / `short_name` のように、何の名前かを入れる。

## 8. モジュールの先頭

モジュールの最初の docstring は、`"""` だけの行で始めて `"""` だけの行で終える。そのあとに 1 行あけて import を書く。
2 行目以降の説明は、空行をはさんで続ける。

```python
"""
ガイドの編集。どの関数も元のガイドは変えず、新しいガイドを返す。
"""

from __future__ import annotations

from dataclasses import replace
```

```python
"""
Maya のノードの名前と API の型 (MObject / MDagPath) の変換。

名前は、同じ名前のノードがあっても 1 つに決まるフルパスで扱うのを基本にする。
"""

import maya.api.OpenMaya as om
```

クラス・関数の docstring は今までどおり (`"""` の直後に 1 行目を書く)。

## 9. ログのレベル

ログは `utils.log` の 4 つから選ぶ。今のレベル (既定は `constants.DEFAULT_LOG_LEVEL` = INFO) より下のものは出ない。

| 関数 | 何を出すか | 例 |
|---|---|---|
| `log.debug` | 開発のときだけ見たいもの (途中の値・操作の記録) | クリックした頂点、ツールを有効にした |
| `log.info` | 使う人にも見せる結果 | 「8 本のエッジでカットしました」 |
| `log.warning` | 思ったとおりにできなかったこと (使う人が直せる) | メッシュを選んでいない、点がつながっていない |
| `log.error` | ツールの不具合・続けられない失敗 | 想定していない例外 |

開発のときは `log.set_level(log.DEBUG)` (名前 `"DEBUG"` でもよい)。レベルは環境変数 `UVSEAMTOOL_LOG_LEVEL` に
持つので、リロードしても変わらない。`print` は使わない。
