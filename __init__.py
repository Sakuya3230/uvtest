# -*- coding: utf-8 -*-
"""
UVPathCut: 頂点 / エッジのあいだの最短パスをプレビューして確定し、UV をカット / 縫合するツール。

    import UVPathCut
    UVPathCut.tool()              # プラグインを読み込んで、このツールにする

開発中のリロード:

    import UVPathCut.reloader as r; r.reload().reload_modules()
    import UVPathCut; UVPathCut.tool()

構成と段階ごとの解説は docs/README.md。Python 3 だけ (Maya 2022〜)。
"""
from .api import *
