# -*- coding: utf-8 -*-
"""
操作の表 (Maya に依存しない)。ボタン・キー・ツール設定のウィンドウは、この表から作る。

    state = ActionState(settings.values(), pending=2, segments=3, has_start=True)
    action = action_by_id("applyCut")
    action.label(state)      # "カット 2"
    action.enabled(state)    # True (ためた区間があるので押せる)

段階 11: キー (key=KeyBinding("Tab")) も表に持つ。tool/keys.py のフィルターがこの表から受け取るキーを作る。
段階 16: モード (パス / 選択)。modes でボタンを出すモードを決める (visible_actions)。button=False は
        キーだけの操作 (E / V)。value を持つ操作は、設定を切り替えずにその値にする。
        カット / 縫合 (C / S) は、パスのモードではためた区間、選択のモードでは選んでいるエッジに効く
        (コンテキストの applyOperation がモードで振り分ける。ボタンの数も、ためた区間の数 / 選んだエッジの数)。

操作を足すときは ACTIONS に 1 行足す。中身は 2 通り:
    setting="pickMode"          設定を切り替える (選択肢は次のもの、真偽値は反対)。コンテキストが Settings.set
    setting=..., value="edge"   設定をその値にする (段階 16。E / V のキー)
    method="applyPending",      コンテキストのメソッドを呼ぶ (args を渡す)
    args=("cut",)

旧版では、操作の情報が 5 か所 (操作の名前の定数・ボタンの並び・キーの表・runAction の if の連鎖・
ツール設定の MEL) に散らばっていて、操作を足すたびに全部を直す必要があった。
"""
from .settings import BOOL, CHOICE, definition, normalize

__all__ = ["Action", "ActionState", "ACTIONS", "GROUPS", "KeyBinding", "action_by_id",
           "action_index", "visible_actions", "next_setting_value", "key_bindings", "key_help",
           "MODE_PATH", "MODE_SELECT", "MODE_RING"]

MODE_PATH = "path"      # パスのモード (設定 mode の選択肢と同じ名前)
MODE_SELECT = "select"  # 選択のモード
MODE_RING = "ring"      # 輪切りのモード (段階 19)

# 組 (ボタンの並びで、組の間を少し空ける)
GROUP_TOGGLE = "toggle"   # 設定の切り替え
GROUP_APPLY = "apply"     # ためた区間をまとめて実行
GROUP_CLEAR = "clear"     # リセット
GROUPS = (GROUP_TOGGLE, GROUP_APPLY, GROUP_CLEAR)

_SHORT_CHOICES = {   # ボタンに出す短い表示名 (選択肢の値 -> 文字)
    ("pickMode", "vertex"): "頂点", ("pickMode", "edge"): "エッジ",
    ("operation", "cut"): "カット", ("operation", "sew"): "縫合",
    ("mode", "path"): "パス", ("mode", "select"): "選択", ("mode", "ring"): "輪切り",
}


class ActionState(object):
    """ボタンの文字・押せるかを決めるための、今の状態 (コンテキストが作る)。"""

    def __init__(self, settings, pending=0, segments=0, has_start=False, mesh_valid=True,
                 selected=0, maya_axis=None):
        self.settings = dict(settings)   # 設定の値 (Settings.values())
        self.selected = selected         # 選んでいる対象のメッシュのエッジの数 (選択のモード。段階 16)
        self.maya_axis = maya_axis       # Maya の対称が効いていればその軸 ("x" など。段階 17)
        self.pending = pending           # まだカット / 縫合していない区間の数
        self.segments = segments         # 確定した区間の数
        self.has_start = has_start       # 未確定のスタートがあるか
        self.mesh_valid = mesh_valid     # 対象のメッシュがまだシーンにあるか


class KeyBinding(object):
    """キー 1 つ (段階 11)。name は Qt のキーの名前 (Qt.Key_<name>。"Tab" / "C" / "Escape" など)。"""

    def __init__(self, name, shift=False, ctrl=False):
        self.name = name
        self.shift = shift
        self.ctrl = ctrl

    def text(self):
        """表示 (Shift+Esc など)。"""
        name = {"Escape": "Esc"}.get(self.name, self.name)
        return "".join(("Ctrl+" if self.ctrl else "", "Shift+" if self.shift else "", name))

    def key(self):
        return (self.name, self.shift, self.ctrl)

    def __repr__(self):
        return "KeyBinding({!r})".format(self.text())


class Action(object):
    """操作 1 つ。"""

    def __init__(self, id, group, label, enabled=None, setting=None, method=None, args=(),
                 description="", key=None, title="", value=None, button=True, modes=None):
        self.id = id
        self.group = group
        self._label = label             # (state) -> 文字
        self._enabled = enabled         # (state) -> bool。None ならいつも押せる
        self.setting = setting          # 切り替える設定のキー (method と排他)
        self.method = method            # 呼ぶコンテキストのメソッドの名前
        self.args = tuple(args)
        self.description = description  # ツールチップ・ツール設定のウィンドウの説明
        self.key = key                  # KeyBinding (無ければ None。段階 11)
        self.title = title or id        # 状態によらない名前 (ツール設定のウィンドウのボタン。段階 12)
        self.value = value              # 設定をこの値にする (None なら切り替え。段階 16)
        self.button = button            # ビューのボタンにするか (False はキーだけ。段階 16)
        self.modes = modes              # ボタンを出すモードのタプル (None ならいつも。段階 16)

    def label(self, state):
        return self._label(state)

    def enabled(self, state):
        return True if self._enabled is None else bool(self._enabled(state))

    def shownIn(self, mode):
        """mode のときにビューのボタンとして出すか (段階 16)。"""
        return self.button and (self.modes is None or mode in self.modes)

    def __repr__(self):
        return "Action({!r})".format(self.id)


def _apply_count(state):
    """カット / 縫合のボタンの数: パスのモードはためた区間、選択のモードは選んだエッジ。"""
    return state.selected if state.settings.get("mode") == MODE_SELECT else state.pending


def _symmetry_label(state):
    """対称のボタン: Maya の対称が効いていれば「Maya 対称 Z」、ツールの対称なら「対称 X」、無ければ「対称 OFF」。"""
    if state.maya_axis:
        return "Maya 対称 {}".format(state.maya_axis.upper())
    if state.settings.get("symmetry"):
        return "対称 {}".format(str(state.settings.get("mirrorAxis", "x")).upper())
    return "対称 OFF"


def _choice_label(key):
    return lambda state: _SHORT_CHOICES.get((key, state.settings[key]), state.settings[key])


ACTIONS = (
    Action("mode", GROUP_TOGGLE, _choice_label("mode"), setting="mode",
           description="モード (パス / 選択 / 輪切り) を切り替える", key=KeyBinding("Tab")),
    Action("pick", GROUP_TOGGLE, _choice_label("pickMode"), setting="pickMode",
           description="拾うもの (頂点 / エッジ) を切り替える", modes=(MODE_PATH,)),
    # キーだけ (ボタンにしない)。選択のモードでも設定は変える (パスのモードに戻ったときに効く)。
    # 受け取らずに Maya に渡すと、E が回転ツールに切り替わってツールを抜けてしまう
    Action("pickEdge", GROUP_TOGGLE, lambda state: "エッジ", setting="pickMode", value="edge",
           description="エッジを拾う", key=KeyBinding("E"), button=False, title="エッジを拾う"),
    Action("pickVertex", GROUP_TOGGLE, lambda state: "頂点", setting="pickMode", value="vertex",
           description="頂点を拾う", key=KeyBinding("V"), button=False, title="頂点を拾う"),
    Action("symmetry", GROUP_TOGGLE, _symmetry_label, setting="symmetry",
           description="対称 (反対側も同じように操作する) を切り替える。Maya の対称がオンの間は Maya の面が"
                       "使われ、両側に効く (ツールの対称を切り替えても変わらない)",
           key=KeyBinding("X")),
    Action("loop", GROUP_TOGGLE,
           lambda state: "ループ ON" if state.settings["loopPreview"] else "ループ OFF",
           setting="loopPreview", description="ループのプレビューを出すかを切り替える",
           key=KeyBinding("L"), modes=(MODE_SELECT,)),
    Action("auto", GROUP_TOGGLE,
           lambda state: "自動 ON" if state.settings["autoCut"] else "自動 OFF",
           setting="autoCut", description="確定と同時にカット / 縫合するかを切り替える",
           modes=(MODE_PATH, MODE_RING)),
    Action("operation", GROUP_TOGGLE,
           lambda state: "自動:" + _SHORT_CHOICES[("operation", state.settings["operation"])],
           setting="operation", description="自動のときの操作 (カット / 縫合) を切り替える",
           modes=(MODE_PATH, MODE_RING)),
    Action("applyCut", GROUP_APPLY, lambda state: "カット {}".format(_apply_count(state)),
           enabled=lambda state: _apply_count(state) > 0 and state.mesh_valid,
           method="applyOperation", args=("cut",),
           description="パス: ためた区間をまとめてカットする / 選択: 選んでいるエッジをカットする",
           key=KeyBinding("C"), title="まとめてカット"),
    Action("applySew", GROUP_APPLY, lambda state: "縫合 {}".format(_apply_count(state)),
           enabled=lambda state: _apply_count(state) > 0 and state.mesh_valid,
           method="applyOperation", args=("sew",),
           description="パス: ためた区間をまとめて縫合する / 選択: 選んでいるエッジを縫合する",
           key=KeyBinding("S"), title="まとめて縫合"),
    Action("clear", GROUP_CLEAR, lambda state: "クリア",
           enabled=lambda state: state.segments > 0 or state.has_start, method="clearAll",
           description="確定した区間・スタート・エッジの選択をすべて外す (UV のカットは戻さない。Ctrl+Z で戻せる)",
           key=KeyBinding("Escape", shift=True), title="クリア"),
)

_BY_ID = {action.id: action for action in ACTIONS}
_INDEX = {action.id: index for index, action in enumerate(ACTIONS)}


def action_by_id(action_id):
    """ID の操作。知らない ID なら KeyError。"""
    return _BY_ID[action_id]


def action_index(action_id):
    """表の番号 (ボタンのハンドルの名前に使う。見えるボタンが変わっても同じ番号。段階 16)。"""
    return _INDEX[action_id]


def visible_actions(mode=MODE_PATH, actions=ACTIONS):
    """mode のときにビューのボタンにする操作 (表の順。段階 16)。"""
    return [action for action in actions if action.shownIn(mode)]


def next_setting_value(key, value):
    """設定を切り替えたときの次の値 (真偽値は反対、選択肢は次のもの。最後の次は最初)。"""
    setting = definition(key)
    if setting.kind == BOOL:
        return not normalize(key, value)
    if setting.kind == CHOICE:
        choices = setting.choices
        return choices[(choices.index(normalize(key, value)) + 1) % len(choices)]
    raise ValueError("{} は切り替えられない種類の設定です".format(key))


def key_bindings(actions=ACTIONS):
    """[(KeyBinding, 操作の ID)] (キーのある操作だけ。段階 11)。同じキーが 2 つあれば ValueError。"""
    bindings = [(action.key, action.id) for action in actions if action.key is not None]
    keys = [binding.key() for binding, _id in bindings]
    if len(keys) != len(set(keys)):
        raise ValueError("同じキーの操作が 2 つあります: {}".format(keys))
    return bindings


def key_help(actions=ACTIONS):
    """キーの説明 ("Tab 頂点 / エッジ  C まとめてカット ...")。ヘルプライン・ツール設定に出す。"""
    names = {"mode": "モード", "pick": "頂点 / エッジ", "pickEdge": "エッジ",
             "pickVertex": "頂点", "symmetry": "対称", "loop": "ループの表示", "applyCut": "まとめてカット", "applySew": "まとめて縫合",
             "clear": "クリア"}
    return "  ".join("{} {}".format(binding.text(), names.get(action_id, action_id))
                     for binding, action_id in key_bindings(actions))
