# -*- coding: utf-8 -*-
"""
プラグインとパッケージの両方が使う名前 (Maya に依存しない)。

プラグイン (plug-ins/uvPathCut.py) は initializePlugin でこのモジュールを読み、ここにある名前で
コマンドを登録する。パッケージの側 (ツールのコマンドなど) も同じ名前でコマンドを呼ぶので、
名前を 1 か所にまとめておく。
"""

PLUGIN_NAME = "uvPathCut"            # プラグインの名前 (plug-ins/uvPathCut.py のファイル名)
CONTEXT_COMMAND = "uvPathCutCtx"     # コンテキストを作る / 編集する / 問い合わせるコマンド
TOOL_COMMAND = "uvPathCutTool"       # このツールにするコマンド (コンテキストを作るか使い回す)
TOOL_CONTEXT = "uvPathCutContext"    # uvPathCutTool が作って使うコンテキストの名前
EDIT_COMMAND = "uvPathCutEdit"       # 確定・カット / 縫合を 1 回の Undo で行うコマンド (段階 8)
LOG_PREFIX = "UV パスカット"          # スクリプトエディタに出すメッセージの頭
MANIP_NODE = "uvPathCutManip"         # マニピュレータのノードの型の名前
# マニピュレータのノードの型の番号。0x00000000〜0x0007ffff は社内・個人用 (配布しないもの) の範囲。
# 旧版 (plug-ins/old/uvPathCut_v1.py) と同じ番号なので、同時には読み込めない
MANIP_TYPE_ID = 0x0007F202

# プラグインが登録するもの。コマンド・ノードを足したら、ここにも足す。
# リロード (reloader.reload_modules) のあとに、読み込み済みのプラグインにこれがそろっているかを
# 確かめ、足りなければプラグインを読み直す (api.ensure_plugin_current)。登録はプラグインを
# 読み込んだとき (initializePlugin) にしか行われないので、モジュールのリロードだけでは増えない
PLUGIN_COMMANDS = (CONTEXT_COMMAND, TOOL_COMMAND, EDIT_COMMAND)
PLUGIN_NODES = (MANIP_NODE,)
