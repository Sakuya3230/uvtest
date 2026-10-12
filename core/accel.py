# -*- coding: utf-8 -*-
"""
numpy / scipy が使えるか (速くする計算で使う。無ければ Python の実装に戻す)。

    from UVPathCut.core import accel
    modules = accel.scipy_modules()      # 使えれば (numpy, scipy.sparse, scipy.sparse.csgraph, scipy.spatial)
    if modules is None: ...               # 使えない -> Python の実装

numpy / scipy は scripts/site-packages/<Maya の版> に入っていて、起動用のバッチ (maya20XX.bat) が
PYTHONPATH に足す。バッチを通さずに起動した Maya や、pytest の Python (Anaconda の numpy が
DLL の読み込みで失敗する) では使えないので、使えなければ None を返す。

使うのは「計算そのものが scipy にある」ときだけ (最短経路 csgraph.dijkstra・近い点 spatial.cKDTree)。
numpy で配列にしただけでは、Python のループが残って速くならないことが多い (対称の対応表で確認)。

テストや比べるときは set_enabled(False) で使わないようにできる (Python の実装になる)。
環境変数 UVPATHCUT_NO_SCIPY=1 でも使わない。
"""
import os

__all__ = ["scipy_modules", "available", "set_enabled", "enabled"]

_MODULES = []        # 調べた結果 [modules か None] (最初に調べたときに入れる)
_ENABLED = [os.environ.get("UVPATHCUT_NO_SCIPY", "") not in ("1", "true")]


def _load():
    try:
        import numpy
        import scipy.sparse
        import scipy.sparse.csgraph
        import scipy.spatial
    except Exception:   # ImportError のほか、壊れた numpy は別の例外も出しうる
        return None
    return numpy, scipy.sparse, scipy.sparse.csgraph, scipy.spatial


def scipy_modules():
    """(numpy, scipy.sparse, scipy.sparse.csgraph, scipy.spatial)。使えない・使わないなら None。"""
    if not _ENABLED[0]:
        return None
    if not _MODULES:
        _MODULES.append(_load())   # import は重いので 1 回だけ試す
    return _MODULES[0]


def available():
    """numpy / scipy を使うか (使える、かつ使わないようにしていない)。"""
    return scipy_modules() is not None


def set_enabled(flag):
    """使うかどうかを切り替える (テスト・比べるとき)。前の値を返す。"""
    previous = _ENABLED[0]
    _ENABLED[0] = bool(flag)
    return previous


def enabled():
    return _ENABLED[0]
