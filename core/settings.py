# -*- coding: utf-8 -*-
"""
設定の定義表と、設定の値を持つ Settings (Maya に依存しない)。

    settings = Settings()                 # 既定値
    settings.value("pickMode")            # "edge"
    settings.set("pickMode", "vertex")    # 正規化して変え、リスナーに知らせる
    settings.set("pickMode", "0")         # 選択肢は番号 (文字列でも) でもよい -> "vertex"

設定を足すときは DEFINITIONS に 1 行足す。正規化・保存・コンテキストのコマンドのフラグ
(tool/context.py)・ツール設定のウィンドウ (段階 12) は、この表から作る。

種類 (Setting.kind):
    BOOL    真偽値。True / False (と 1 / 0、"true" / "false" などの文字列)
    CHOICE  選択肢の名前のどれか。番号 (0, 1, ...) や数字の文字列も受け付ける
    FLOAT   小数。範囲 (minimum, maximum) の外は端に寄せる
    COLOR   色 (r, g, b)。0〜1 の 3 つの数 (リスト・タプル・"r g b" / "r,g,b" の文字列)。0〜1 に寄せる。
            コンテキストのコマンドのフラグは作らない (問い合わせは数を 1 つしか返せないため。
            -setColor "キー r g b" と、ツール設定のウィンドウからは Python の関数で受け渡す)
"""

__all__ = ["BOOL", "CHOICE", "FLOAT", "COLOR", "Setting", "SettingsError", "DEFINITIONS",
           "definition", "normalize", "normalize_all", "defaults", "Settings", "keys_in_section"]

BOOL = "bool"
CHOICE = "choice"
FLOAT = "float"
COLOR = "color"


class SettingsError(ValueError):
    """設定の値が直せない (知らないキー・選択肢に無い名前など)。"""


class Setting(object):
    """設定の 1 項目の定義。"""

    def __init__(self, key, kind, default, short_flag, label, choices=(), choice_labels=(),
                 minimum=None, maximum=None, description="", section="設定", check_label="",
                 precision=2):
        self.key = key                  # 設定の名前 (フラグの長い名前・保存のキーにも使う)
        self.kind = kind                # BOOL / CHOICE / FLOAT
        self.default = default
        self.short_flag = short_flag    # コンテキストのコマンドの短いフラグ ("-pm" など。COLOR は None)
        self.label = label              # 表示名 (ツール設定のウィンドウ)
        self.choices = tuple(choices)   # CHOICE の選択肢の名前 (問い合わせはこの番号を返す)
        self.choice_labels = tuple(choice_labels) or self.choices   # 選択肢の表示名
        self.minimum = minimum          # FLOAT の範囲
        self.maximum = maximum
        self.description = description
        self.section = section          # ツール設定のウィンドウの欄 (段階 12)
        self.check_label = check_label  # BOOL のチェックボックスの横の文字 (見出しは label)
        self.precision = precision      # FLOAT の欄の小数の桁数 (ツール設定のウィンドウ)

    @property
    def long_flag(self):
        return "-" + self.key

    def __repr__(self):
        return "Setting({!r}, {!r}, default={!r})".format(self.key, self.kind, self.default)


# 設定の定義表。段階ごとに 1 行ずつ足す
DEFINITIONS = (
    Setting("mode", CHOICE, "path", "-md", "モード",
            choices=("path", "select", "ring"), choice_labels=("パス", "選択", "輪切り"),
            description="パス: クリックでスタート / 確定。選択: クリック・ダブルクリック (ループ)・ドラッグ (矩形) で"
                        "エッジを選び、ボタン / C / S でカット / 縫合 (段階 16)。輪切り: 筒を横切るように"
                        "ドラッグして、一周するループをプレビューし、クリックで確定 (段階 19)",
            section="モード"),
    Setting("loopPreview", BOOL, False, "-lp", "ループ",
            description="選択のモードで、マウスの下のエッジから、ダブルクリックで選ばれるループを出す "
                        "(オフなら、マウスの下のエッジ 1 本だけを強調する)",
            section="モード", check_label="選択のモードでループをプレビューする"),
    Setting("ringSmooth", BOOL, True, "-rsm", "なめらか",
            description="輪切りで離したときに、今あるループに吸い付ける / 境目の近くで面に沿う道に引き直す "
                        "(段差を減らす。段階 20)。オフなら境目 (段差あり) のまま",
            section="輪切り", check_label="離したときに輪切りをなめらかにする"),
    Setting("pickMode", CHOICE, "edge", "-pm", "拾うもの",
            choices=("vertex", "edge"), choice_labels=("頂点", "エッジ"),
            description="マウスの下の頂点とエッジのどちらを拾うか", section="パス"),
    Setting("straightness", FLOAT, 1.0, "-st", "まっすぐさ", minimum=0.0, maximum=10.0,
            description="曲がりの少ないパスを選ぶ重み (段階 15)。0 で長さだけの最短。"
                        "大きいほど、遠回りしても曲がりを避ける (直角 1 回 = 重み × 平均のエッジの長さ)",
            section="パス"),
    Setting("symmetry", BOOL, False, "-sy", "対称",
            description="反対側も同じように操作する (段階 17)。反対側は位置で決める。面は下の空間と軸。"
                        "Maya の対称がオン (ワールド / オブジェクト) の間は、Maya の面で両側に効く",
            section="対称", check_label="反対側も同じように操作する"),
    Setting("mirrorSpace", CHOICE, "object", "-ms", "空間",
            choices=("world", "object"), choice_labels=("ワールド", "オブジェクト"),
            description="対称の面の空間 (ワールド: ワールドの原点を通る面 / オブジェクト: Transform の原点を通る面)",
            section="対称"),
    Setting("mirrorAxis", CHOICE, "x", "-ma", "軸",
            choices=("x", "y", "z"), choice_labels=("X", "Y", "Z"),
            description="対称の面に垂直な軸 (X なら左右)",
            section="対称"),
    Setting("mirrorTolerance", FLOAT, 0.1, "-mt", "許容値", minimum=0.0001, maximum=10.0,
            description="反対側の頂点を探す距離 (鏡映した位置からこの距離の中で最も近い頂点)",
            section="対称", precision=4),
    Setting("autoCut", BOOL, True, "-ac", "自動",
            description="オンなら、パスを確定すると同時にカット / 縫合する", section="カット / 縫合",
            check_label="確定と同時に実行する"),
    Setting("operation", CHOICE, "cut", "-op", "自動のときの操作",
            choices=("cut", "sew"), choice_labels=("カット", "縫合"),
            description="自動のときに行う操作", section="カット / 縫合"),
    # 色 (表示の色。core.draw_list.COLOR_ROLES で描画の役割に当てる)
    Setting("faceColor", COLOR, (0.35, 0.95, 0.45), None, "マウスの下の面",
            description="マウスの下の面の塗りと縁", section="色"),
    Setting("pickColor", COLOR, (1.00, 0.60, 0.15), None, "拾った頂点 / エッジ",
            description="マウスの下で拾った頂点 / エッジ (エンドの候補)", section="色"),
    Setting("startColor", COLOR, (0.25, 1.00, 0.35), None, "スタート",
            description="スタートの頂点 / エッジ", section="色"),
    Setting("pathColor", COLOR, (1.00, 0.85, 0.20), None, "プレビュー",
            description="パスとループのプレビュー (反対側はこの色をうすく)", section="色"),
    Setting("pendingColor", COLOR, (1.00, 0.30, 0.85), None, "未実行の区間",
            description="確定したが、まだカット / 縫合していない区間と、区間の端点の印", section="色"),
    Setting("cutColor", COLOR, (1.00, 0.30, 0.30), None, "カットした区間",
            description="カットした区間", section="色"),
    Setting("sewColor", COLOR, (0.40, 0.95, 0.40), None, "縫合した区間",
            description="縫合した区間", section="色"),
)

_BY_KEY = {setting.key: setting for setting in DEFINITIONS}
_TRUE = ("1", "true", "on", "yes")
_FALSE = ("0", "false", "off", "no")


def definition(key):
    """キーの定義 (Setting)。知らないキーなら SettingsError。"""
    try:
        return _BY_KEY[key]
    except KeyError:
        raise SettingsError("知らない設定です: {}".format(key))


def normalize(key, value):
    """値を、その設定の型・選択肢・範囲に直す。直せなければ SettingsError。"""
    setting = definition(key)
    if setting.kind == BOOL:
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in (0, 1):
            return bool(value)
        text = str(value).strip().lower()
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
        raise SettingsError("{} は真偽値です: {!r}".format(key, value))
    if setting.kind == CHOICE:
        if value in setting.choices:
            return value
        text = str(value).strip()
        if text in setting.choices:
            return text
        if text.isdigit() and int(text) < len(setting.choices):
            return setting.choices[int(text)]   # 番号 (問い合わせが返すもの) でもよい
        raise SettingsError("{} は {} のどれか (または番号) です: {!r}".format(
            key, " / ".join(setting.choices), value))
    if setting.kind == FLOAT:
        if isinstance(value, bool):
            raise SettingsError("{} は数です: {!r}".format(key, value))
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise SettingsError("{} は数です: {!r}".format(key, value))
        if setting.minimum is not None:
            number = max(setting.minimum, number)
        if setting.maximum is not None:
            number = min(setting.maximum, number)
        return number
    if setting.kind == COLOR:
        if isinstance(value, str):
            value = value.replace(",", " ").split()
        try:
            rgb = tuple(min(1.0, max(0.0, float(c))) for c in value)
        except (TypeError, ValueError):
            raise SettingsError("{} は色 (0〜1 の 3 つの数) です: {!r}".format(key, value))
        if len(rgb) != 3 or any(isinstance(c, bool) for c in value):
            raise SettingsError("{} は色 (0〜1 の 3 つの数) です: {!r}".format(key, value))
        return rgb
    raise SettingsError("知らない種類です: {}".format(setting.kind))


def keys_in_section(section):
    """欄の設定のキー (定義表の順)。"""
    return [setting.key for setting in DEFINITIONS if setting.section == section]


def defaults():
    """既定値の dict (定義表の順)。"""
    return {setting.key: setting.default for setting in DEFINITIONS}


def normalize_all(data):
    """保存していた dict などを、使える値だけの dict にする。

    知らないキーは捨て、直せない値と無いキーは既定値にする (古い・壊れた保存でも動くように)。
    """
    values = defaults()
    if not isinstance(data, dict):
        return values
    for key in values:
        if key in data:
            try:
                values[key] = normalize(key, data[key])
            except SettingsError:
                pass
    return values


class Settings(object):
    """設定の値。変えると保存し (storage があれば)、リスナーに知らせる。

    storage は load() -> dict か None と save(dict) を持つもの (Maya では scene/prefs.py の
    OptionVarStorage。テストでは辞書で代わりをする)。作ったときに load して正規化する。
    リスナーは listener(key, value) で、値が変わったときだけ呼ぶ。
    """

    def __init__(self, storage=None):
        self._storage = storage
        self._values = normalize_all(storage.load() if storage is not None else None)
        self._listeners = []

    def value(self, key):
        definition(key)   # 知らないキーなら SettingsError
        return self._values[key]

    def values(self):
        """今の値の dict (写し)。"""
        return dict(self._values)

    def set(self, key, value):
        """値を正規化して変える。変わったら保存してリスナーに知らせる。直した値を返す。"""
        value = normalize(key, value)
        if self._values[key] != value:
            self._values[key] = value
            self._save()
            for listener in list(self._listeners):
                listener(key, value)
        return value

    def reset(self, keys=None):
        """すべて (keys を渡せばそれだけ) 既定値に戻す (変わった項目ごとにリスナーに知らせる)。"""
        for key, value in defaults().items():
            if keys is None or key in keys:
                self.set(key, value)

    def addListener(self, listener):
        if listener not in self._listeners:
            self._listeners.append(listener)

    def removeListener(self, listener):
        if listener in self._listeners:
            self._listeners.remove(listener)

    def choiceIndex(self, key):
        """CHOICE の今の値の番号 (コンテキストのコマンドの問い合わせが返すもの)。"""
        setting = definition(key)
        if setting.kind != CHOICE:
            raise SettingsError("{} は選択肢ではありません".format(key))
        return setting.choices.index(self._values[key])

    def _save(self):
        if self._storage is not None:
            self._storage.save(self.values())
