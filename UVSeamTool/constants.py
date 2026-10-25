"""
プラグインとパッケージが共有する名前と、ファイルの置き場所。

パッケージの中のものは import しない (どのフォルダからも使えるように)。
"""

import os
import tempfile

TOOL_NAME           = "UVSeamTool"

PLUGIN_NAME         = "uvSeamTool"          # plug-ins/uvSeamTool.py
CONTEXT_COMMAND     = "uvSeamToolCtx"       # コンテキストを作るコマンド (プラグインが登録する)
CONTEXT_NAME        = "uvSeamToolContext"   # 作ったコンテキストの名前 (1 つを使い回す)
TOOL_CLASS          = "uvSeamTool"          # コンテキストの stringClassName。ツール設定のウィンドウの MEL の入り口の名前の元
EDIT_COMMAND        = "uvSeamToolEdit"      # Undo できる操作のコマンド (utils.undo。プラグインが登録する)
PLUGIN_COMMANDS     = (CONTEXT_COMMAND, EDIT_COMMAND)   # プラグインが登録するコマンド (足りなければ読み直す)

GUIDE_ATTRIBUTE     = "uvSeamToolGuides"    # ガイドを保存する、メッシュのシェイプの文字列のアトリビュート (シーンに残る)

DEFAULT_LOG_LEVEL   = "INFO"                    # これより下のレベルのログは出さない (utils.log)
LOG_LEVEL_ENV       = "UVSEAMTOOL_LOG_LEVEL"    # 今のレベルを持つ環境変数 (リロードしても変わらないように)

# 設定の書き出し先 (段階で使う)。今はユーザーの一時フォルダ。後で任意の場所に変える
SETTINGS_PATH       = os.path.join(tempfile.gettempdir(), TOOL_NAME, "settings.json")
