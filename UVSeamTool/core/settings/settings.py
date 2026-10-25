"""
設定の今の値 (表 core.settings.definitions の項目ごと)。

    from ..core.settings import settings
    settings.current().value("guideColor")

current() はパッケージに 1 つの Settings。初めて呼んだときに constants.SETTINGS_PATH のファイルから読む。
"""

from __future__ import annotations

from ...constants import SETTINGS_PATH
from .definitions import BY_KEY, DEFINITIONS
from .json_storage import JsonStorage
from .setting import BOOL, CHOICE, COLOR, FLOAT


class Settings:
    """設定の今の値を持ち、変えたら保存してリスナーに知らせる。

    保存するのは既定と違う値だけ。知らないキー・直せない値は読むときに飛ばす (別の版で足した項目があっても壊れない)。
    """

    # -- 特殊メソッド ---------------------------------------------------------
    def __init__(self, storage=None):
        self._storage   = storage       # JsonStorage (None なら保存しない)
        self._values    = {setting.key: setting.default for setting in DEFINITIONS}
        self._listeners = []

        if storage is not None:
            for key, value in storage.load().items():
                if key in BY_KEY:
                    try:
                        self._values[key] = normalize(key, value)
                    except ValueError:
                        pass   # 直せない値は既定のまま

    # -- 公開メソッド ---------------------------------------------------------
    def value(self, key):
        return self._values[key]

    def values(self):
        """すべての値の dict (写し)。"""
        return dict(self._values)

    def setValue(self, key, value):
        """値を変える (直せなければ ValueError)。変わったら保存して、リスナーに知らせる。"""
        value = normalize(key, value)
        if self._values[key] == value:
            return

        self._values[key] = value
        self._save()
        self._notify(key)

    def reset(self, keys=None):
        """keys (省くとすべて) を既定の値に戻す。"""
        for key in keys if keys is not None else list(BY_KEY):
            self.setValue(key, BY_KEY[key].default)

    def addListener(self, listener):
        """listener(key) を、値が変わるたびに呼ぶ。"""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def removeListener(self, listener):
        if listener in self._listeners:
            self._listeners.remove(listener)

    # -- 非公開メソッド -------------------------------------------------------
    def _save(self):
        if self._storage is None:
            return

        changed = {key: list(value) if isinstance(value, tuple) else value
                   for key, value in self._values.items() if value != BY_KEY[key].default}
        self._storage.save(changed)

    def _notify(self, key):
        for listener in list(self._listeners):
            listener(key)


def normalize(key, value):
    """値を項目の種類に合わせて直す。直せなければ ValueError。

    色 = 0〜1 の float 3 つの tuple / BOOL = bool / CHOICE = choices の値のどれか / FLOAT = 範囲に寄せた float。
    """
    setting = BY_KEY.get(key)
    if setting is None:
        raise ValueError("設定の項目ではありません: {}".format(key))

    if setting.kind == COLOR:
        try:
            red, green, blue = (float(component) for component in value)
        except (TypeError, ValueError):
            raise ValueError("{} は (r, g, b) の色です: {!r}".format(key, value))

        return tuple(min(1.0, max(0.0, component)) for component in (red, green, blue))

    if setting.kind == BOOL:
        if not isinstance(value, (bool, int)):
            raise ValueError("{} はオン / オフです: {!r}".format(key, value))
        return bool(value)

    if setting.kind == CHOICE:
        values = [choice for choice, _ in setting.choices]
        if value not in values:
            raise ValueError("{} は {} のどれかです: {!r}".format(key, " / ".join(values), value))
        return value

    if setting.kind == FLOAT:
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError("{} は数です: {!r}".format(key, value))
        return min(setting.maximum, max(setting.minimum, number))

    raise ValueError("知らない種類です: {}".format(setting.kind))


_CURRENT = None


def current():
    """パッケージに 1 つの Settings (初めて呼んだときに設定のファイルから読む)。"""
    global _CURRENT

    if _CURRENT is None:
        _CURRENT = Settings(JsonStorage(SETTINGS_PATH))

    return _CURRENT


def install(new_settings):
    """current() が返す Settings を替える (テスト用。Settings() を渡せば既定値のまま、ファイルに保存しない)。"""
    global _CURRENT

    _CURRENT = new_settings
