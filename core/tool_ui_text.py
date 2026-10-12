# -*- coding: utf-8 -*-
"""
ツール設定のウィンドウの MEL を、設定の定義表と操作の表から組み立てる (Maya に依存しない。段階 12)。

    text = tool_ui_mel()     # tool/tool_ui.py が mel.eval で定義する

ツールのアイコンをダブルクリックすると開くウィンドウは、Maya が MEL のプロシージャを呼んで作る:
    <クラス名>Properties             部品を作る (値は入れない)
    <クラス名>Values(ツールの名前)   ツールを有効にするたび・ウィンドウを開くたびに呼ばれる。
                                     今の値を部品に入れ、操作したらコンテキストのコマンドで値を変える
クラス名はコンテキストの stringClassName() ("uvPathCut")。レイアウトの名前も同じにする。

部品は設定の種類ごと (どれも左に同じ幅の見出しの列を持つ ...Grp の部品にして、左端を揃える):
    BOOL    checkBoxGrp (見出し + チェック)       -changeCommand で uvPathCutCtx -e -<キー> #1
    CHOICE  radioButtonGrp (選択肢の表示名)       -onCommandN で uvPathCutCtx -e -<キー> <選択肢>
    FLOAT   floatSliderGrp (範囲)                 -changeCommand で uvPathCutCtx -e -<キー> #1
    COLOR   colorSliderGrp (クリックで色を選ぶ)   -changeCommand で uvPathCutSetColor (-setColor "キー r g b")
説明は部品のツールチップ (-annotation) にする (説明の行を並べると、ごちゃごちゃして見えた)。
メソッドの操作 (まとめてカット・縫合・クリア) はボタンで、uvPathCutCtx -e -runAction <ID>。
操作のグループ (Action.group) ごとに行を分ける (まとめて実行 と クリア は別の行)。
設定・操作を表に足せば、ウィンドウにもそろって出る (旧版は MEL を手で書き足していた)。

色の値は、コンテキストのコマンドの問い合わせでは受け取れない (数を 1 つしか返せない) ので、
MEL の python() で tool/tool_ui.py の color_value を呼ぶ (Python のリストが MEL の float[] になる)。

旧版で確かめた落とし穴:
- Values の先頭で setParent (toolPropertyWindow -q -location + "|uvPathCut") してから、部品を名前だけで
  操作する。しないと「Object not found」
- Properties はそのクラス名で最初に使ったときの 1 回しか呼ばれないらしい (プラグインを読み直すと前の版の
  部品が残る)。Values の先頭で古いレイアウトを消して、Properties を自分で呼び直す
- 問い合わせは文字列を返せないので、選択肢は番号で返る (radioButtonGrp の -select は 1 から)
"""
from .actions import ACTIONS, key_help
from .settings import BOOL, CHOICE, COLOR, DEFINITIONS, FLOAT

__all__ = ["CLASS_NAME", "control_name", "tool_ui_mel", "sections", "COLLAPSED_SECTIONS"]

CLASS_NAME = "uvPathCut"   # コンテキストの stringClassName と同じ
CONTEXT_COMMAND = "uvPathCutCtx"
LABEL_WIDTH = 140          # 見出しの列の幅 (すべての部品で揃える)
CHOICE_WIDTH = 90          # ラジオボタン 1 つの幅 (広がりすぎないように)
BUTTON_WIDTH = 110         # ボタンの幅 (同じ幅にする)
COLOR_SWATCH_WIDTH = 50    # 色の四角の幅
COLOR_SLIDER_WIDTH = 160   # 色の明るさのスライダーの幅
COLLAPSED_SECTIONS = ("色",)   # 最初はたたんでおく欄
COLOR_SECTION = "色"
SYMMETRY_SECTION = "対称"
# Maya の対称が効いている間は灰色にする設定 (段階 17。Maya の面を使うため)
MAYA_SYMMETRY_KEYS = ("mirrorSpace", "mirrorAxis", "mirrorTolerance")
_MAYA_TEXT = "{}_mayaSymmetry".format(CLASS_NAME)
TOOL_UI_MODULE = "UVPathCut.tool.tool_ui"


def control_name(key):
    """設定 / 操作の部品の名前 (MEL で名前だけで操作する)。"""
    return "{}_{}".format(CLASS_NAME, key)


def mel_string(text):
    """MEL の文字列のリテラル (" と \\ をエスケープする)。"""
    return '"{}"'.format(text.replace("\\", "\\\\").replace('"', '\\"'))


def sections(definitions=DEFINITIONS):
    """[(欄の名前, [設定の定義])] (欄は定義表に出てくる順)。"""
    order = []
    for setting in definitions:
        if setting.section not in order:
            order.append(setting.section)
    return [(name, [s for s in definitions if s.section == name]) for name in order]


def _setting_control(setting):
    """設定 1 つの部品を作る MEL の行 (Properties の中)。"""
    name = control_name(setting.key)
    label = mel_string(setting.label)
    tip = "-annotation {} ".format(mel_string(setting.description)) if setting.description else ""
    first = "-columnWidth 1 {} ".format(LABEL_WIDTH)
    if setting.kind == BOOL:
        return "checkBoxGrp -numberOfCheckBoxes 1 -label {} -label1 {} {}{}{};".format(
            label, mel_string(setting.check_label), first, tip, name)
    if setting.kind == CHOICE:
        count = len(setting.choices)
        if not 2 <= count <= 4:
            raise ValueError("radioButtonGrp の選択肢は 2〜4 個: {}".format(setting.key))
        labels = " ".join(mel_string(text) for text in setting.choice_labels)
        widths = " ".join("-columnWidth {} {}".format(i + 2, CHOICE_WIDTH) for i in range(count))
        return "radioButtonGrp -numberOfRadioButtons {} -label {} -labelArray{} {} {}{} {}{};".format(
            count, label, count, labels, first, widths, tip, name)
    if setting.kind == FLOAT:
        return ("floatSliderGrp -label {} -field true -precision {} -minValue {} -maxValue {} "
                "-fieldMinValue {} -fieldMaxValue {} {}{}{};").format(
            label, setting.precision, setting.minimum, setting.maximum, setting.minimum,
            setting.maximum, first, tip, name)
    if setting.kind == COLOR:
        # 列の幅を決めないと、色の四角が横に伸びてスライダーが見えなくなる
        return "colorSliderGrp -label {} -columnWidth3 {} {} {} {}{};".format(
            label, LABEL_WIDTH, COLOR_SWATCH_WIDTH, COLOR_SLIDER_WIDTH, tip, name)
    raise ValueError("知らない種類です: {}".format(setting.kind))


def _setting_command(setting):
    """設定 1 つの部品に、変えたときのコマンドを付ける MEL の行 (Values の中)。"""
    name = control_name(setting.key)
    if setting.kind == CHOICE:
        parts = ['-onCommand{} ("{} -edit -{} {} " + $toolName)'.format(
            i + 1, CONTEXT_COMMAND, setting.key, choice) for i, choice in enumerate(setting.choices)]
        return "radioButtonGrp -edit {} {};".format(" ".join(parts), name)
    if setting.kind == COLOR:
        return 'colorSliderGrp -edit -changeCommand ("{}SetColor {} " + $toolName) {};'.format(
            CLASS_NAME, setting.key, name)
    if setting.kind == BOOL:
        return 'checkBoxGrp -edit -changeCommand1 ("{} -edit -{} #1 " + $toolName) {};'.format(
            CONTEXT_COMMAND, setting.key, name)
    return 'floatSliderGrp -edit -changeCommand ("{} -edit -{} #1 " + $toolName) {};'.format(
        CONTEXT_COMMAND, setting.key, name)


def _color_query(key):
    """色の設定の値を Python から受け取る MEL の式 (float[3] になる)。"""
    return 'python("__import__(\'{}\', fromlist=[\'x\']).color_value(\'{}\')")'.format(
        TOOL_UI_MODULE, key)


def _setting_value(setting):
    """設定 1 つの部品に、今の値を入れる MEL の行 (SetValues の中。コマンドは呼ばれない)。"""
    name = control_name(setting.key)
    if setting.kind == COLOR:
        return ("{{ float $c[] = {}; colorSliderGrp -edit -rgb $c[0] $c[1] $c[2] {}; }}").format(
            _color_query(setting.key), name)
    query = "`{} -q -{} $toolName`".format(CONTEXT_COMMAND, setting.key)
    if setting.kind == CHOICE:
        return "radioButtonGrp -edit -select ({} + 1) {};".format(query, name)
    if setting.kind == BOOL:
        return "checkBoxGrp -edit -value1 {} {};".format(query, name)
    return "floatSliderGrp -edit -value {} {};".format(query, name)


_CONTROL_COMMANDS = {BOOL: "checkBoxGrp", CHOICE: "radioButtonGrp", FLOAT: "floatSliderGrp",
                     COLOR: "colorSliderGrp"}


def _text_width(text):
    """ボタンの文字のおおよその幅 (ピクセル)。全角は 12、半角は 7 として、左右の余白 24 を足す。"""
    return sum(12 if ord(ch) > 0xff else 7 for ch in text) + 24


def _button_width(titles):
    """同じ行のボタンの幅: BUTTON_WIDTH か、いちばん長い文字が収まる幅 (10 の倍数に切り上げ)。

    「Maya の設定を読み込む」が BUTTON_WIDTH では見切れた (GUI で確認) ので、文字に合わせて広げる。
    同じ行のボタンは同じ幅のまま (揃って見えるように)。
    """
    widest = max([_text_width(title) for title in titles] + [BUTTON_WIDTH - 4])
    return int(-(-(widest + 4) // 10) * 10)


def _button_row(buttons):
    """見出しの列 (空) の右に、同じ幅のボタンを並べる MEL の行。buttons は [(表示名, 説明, 部品の名前)]。"""
    if not buttons:
        return []
    count = len(buttons) + 1
    width = _button_width([title for title, _tip, _name in buttons])
    widths = " ".join("-columnWidth {} {}".format(i + 2, width) for i in range(len(buttons)))
    lines = ["rowLayout -numberOfColumns {} -columnWidth 1 {} {};".format(count, LABEL_WIDTH, widths),
             '    text -label "";']
    for title, tip, name in buttons:
        lines.append("    button -label {} -width {} -annotation {} {};".format(
            mel_string(title), width - 4, mel_string(tip), name))
    lines.append("setParent ..;")
    return lines


def _method_actions(actions=ACTIONS):
    return [action for action in actions if action.method is not None]


def _action_groups(actions):
    """[[操作]] (Action.group ごと。グループは表に出てくる順)。"""
    groups = []
    for action in actions:
        if groups and groups[-1][0].group == action.group:
            groups[-1].append(action)
        else:
            groups.append([action])
    return groups


def tool_ui_mel(definitions=DEFINITIONS, actions=ACTIONS):
    """ツール設定のウィンドウの MEL のプロシージャ (Properties / Values / SetValues / SetColor / RefreshUI)。"""
    lines = []

    def add(text, depth=0):
        lines.append("    " * depth + text)

    has_colors = any(setting.kind == COLOR for setting in definitions)
    methods = _method_actions(actions)
    # -- Properties: 部品を作る ------------------------------------------------
    add("global proc {}Properties()".format(CLASS_NAME))
    add("{")
    add("setUITemplate -pushTemplate OptionsTemplate;", 1)
    add("string $parent = `toolPropertyWindow -q -location`;", 1)
    add("setParent $parent;", 1)
    add("columnLayout -adjustableColumn true {};".format(CLASS_NAME), 1)
    for section, settings in sections(definitions):
        add("frameLayout -label {} -collapsable true -collapse {};".format(
            mel_string(section), "true" if section in COLLAPSED_SECTIONS else "false"), 2)
        add("columnLayout -adjustableColumn true;", 3)
        for setting in settings:
            add(_setting_control(setting), 4)
        if section == SYMMETRY_SECTION:
            # Maya の対称が効いているとき、その面を出す (SetValues で文字を入れる)
            # 2 列目はウィンドウの幅に合わせて広げる (固定の幅だと文が見切れた)
            add('rowLayout -numberOfColumns 2 -columnWidth 1 {} -adjustableColumn 2;'.format(LABEL_WIDTH), 4)
            add('text -label "";', 5)
            add('text -align "left" -label "" {};'.format(_MAYA_TEXT), 5)
            add("setParent ..;", 4)
        if section == COLOR_SECTION:
            for line in _button_row([("色を既定に戻す", "色の設定だけを既定に戻す",
                                      control_name("resetColors"))]):
                add(line, 4)
        add("setParent ..;", 3)
        add("setParent ..;", 2)
    if methods:
        add('frameLayout -label "操作" -collapsable true -collapse false;', 2)
        add("columnLayout -adjustableColumn true;", 3)
        for group in _action_groups(methods):   # 操作のグループ (まとめて実行 / クリア) ごとに行を分ける
            for line in _button_row([(a.title, a.description, control_name(a.id)) for a in group]):
                add(line, 4)
        add("setParent ..;", 3)
        add("setParent ..;", 2)
    add('frameLayout -label "キーとマウス" -collapsable true -collapse true;', 2)
    add("columnLayout -adjustableColumn true;", 3)
    for text in ("パス: クリックでスタート / 次のクリックでパスを確定 (エンドが次のスタート)",
                 "パス: Esc でスタートを取り消す / Ctrl+Z で 1 区間ずつ戻す",
                 "選択: クリックでエッジ / ダブルクリックでループ / ドラッグで矩形 (表のエッジだけ)",
                 "選択: Shift 切り替え / Ctrl 外す / Ctrl+Shift 足す",
                 "輪切り: ドラッグで一周 (Shift+ドラッグで縦の継ぎ目)、クリックで確定、Esc で捨てる",
                 "輪切り: 離したあと、ホイールでずらす / Shift+ホイールで傾ける",
                 key_help(actions),
                 "(キーはマウスがビューの上にあるときだけ。パスの Shift / Ctrl のクリックは普通の選択)"):
        add('text -align "left" -label {};'.format(mel_string(text)), 4)
    add("setParent ..;", 3)
    add("setParent ..;", 2)
    for line in _button_row([("設定を既定に戻す", "すべての設定 (色も) を既定に戻す",
                              control_name("resetSettings"))]):
        add(line, 2)
    add("setParent ..;", 1)
    add("setUITemplate -popTemplate;", 1)
    add("}")
    add("")
    # -- Values: 古いレイアウトを作り直し、コマンドを付け、値を入れる ----------------------
    add("global proc {}Values(string $toolName)".format(CLASS_NAME))
    add("{")
    add("// Properties は最初の 1 回しか呼ばれないらしいので、古いレイアウトを消して作り直す", 1)
    add('string $parent = `toolPropertyWindow -q -location` + "|{}";'.format(CLASS_NAME), 1)
    add("if (`layout -exists $parent`) deleteUI $parent;", 1)
    add("{}Properties();".format(CLASS_NAME), 1)
    add("setParent $parent;   // 部品を名前だけで操作するため", 1)
    for setting in definitions:
        add(_setting_command(setting), 1)
    for action in methods:
        add('button -edit -command ("{} -edit -runAction {} " + $toolName) {};'.format(
            CONTEXT_COMMAND, action.id, control_name(action.id)), 1)
    if has_colors:
        add('button -edit -command ("{} -edit -resetColors true " + $toolName) {};'.format(
            CONTEXT_COMMAND, control_name("resetColors")), 1)
    add('button -edit -command ("{} -edit -resetSettings true " + $toolName) {};'.format(
        CONTEXT_COMMAND, control_name("resetSettings")), 1)
    add("{}SetValues $toolName;".format(CLASS_NAME), 1)
    add("toolPropertySelect {};".format(CLASS_NAME), 1)
    add("}")
    add("")
    # -- SetValues: 今の値を入れる ------------------------------------------------
    add("global proc {}SetValues(string $toolName)".format(CLASS_NAME))
    add("{")
    for setting in definitions:
        add(_setting_value(setting), 1)
    maya_keys = [s for s in definitions if s.key in MAYA_SYMMETRY_KEYS]
    if maya_keys:
        add("// Maya の対称が効いている間は、ツールの空間・軸・許容値を灰色にして、使っている面を出す", 1)
        add('string $maya = python("__import__(\'UVPathCut.tool.tool_ui\', fromlist=[\'x\'])'
            '.maya_symmetry_text()");', 1)
        add('text -edit -label $maya {};'.format(_MAYA_TEXT), 1)
        for setting in maya_keys:
            add('{} -edit -enable ($maya == "") {};'.format(
                _CONTROL_COMMANDS[setting.kind], control_name(setting.key)), 1)
    add("}")
    add("")
    # -- SetColor: 色のスライダーで選んだ色を、コンテキストのコマンドで設定する -----------------------
    add("global proc {}SetColor(string $key, string $toolName)".format(CLASS_NAME))
    add("{")
    add('setParent (`toolPropertyWindow -q -location` + "|{}");'.format(CLASS_NAME), 1)
    add('float $c[] = `colorSliderGrp -q -rgb ("{}_" + $key)`;'.format(CLASS_NAME), 1)
    add('{} -edit -setColor ($key + " " + $c[0] + " " + $c[1] + " " + $c[2]) $toolName;'.format(
        CONTEXT_COMMAND), 1)
    add("}")
    add("")
    # -- RefreshUI: ボタン・キーで設定を変えたとき、開いているウィンドウを合わせる ------------------
    add("global proc {}RefreshUI()".format(CLASS_NAME))
    add("{")
    add('string $parent = `toolPropertyWindow -q -location` + "|{}";'.format(CLASS_NAME), 1)
    add("if (!`layout -exists $parent`) return;", 1)
    add("string $tool = `currentCtx`;", 1)
    add("// 今のツールがこのツールでなければ、問い合わせが失敗する (catch が 1 を返す)", 1)
    first_flag = next(s.key for s in definitions if s.kind != COLOR)
    add("if (catch(`{} -q -{} $tool`)) return;".format(CONTEXT_COMMAND, first_flag), 1)
    add("string $old = `setParent -q`;", 1)
    add("setParent $parent;", 1)
    add("{}SetValues $tool;".format(CLASS_NAME), 1)
    add('if ($old != "") setParent $old;', 1)
    add("}")
    return "\n".join(lines) + "\n"
