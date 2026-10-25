"""
numpy と scipy を読み込む。

ほかのモジュールは numpy / scipy を直接 import せず、ここの `np` / `sparse` / `csgraph` / `spatial` を使う。
読み込めなかったときは None になり、`require()` が理由を付けて止める。
"""

try:
    import numpy as np
    import scipy.sparse as sparse
    import scipy.sparse.csgraph as csgraph
    import scipy.spatial as spatial
    IMPORT_ERROR = None
except ImportError as error:
    np = None
    sparse = None
    csgraph = None
    spatial = None
    IMPORT_ERROR = str(error)


def require():
    """numpy と scipy が使えなければ RuntimeError を出す。"""
    if IMPORT_ERROR is not None:
        raise RuntimeError(
            "UVSeamTool には numpy と scipy が必要です ({})。"
            "mayapy_getpip*.bat で入れて、maya20XX.bat から Maya を起動してください".format(IMPORT_ERROR))
