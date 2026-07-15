import sys
from pathlib import Path

# 親ディレクトリ（src）を検索パスに追加
sys.path.append(str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP

# 関数定義のみ取得
from utils.tools import get_current_time

mcp = FastMCP("time-server")

# Phase1のLocal Toolをそのまま @mcp.tool() でMCP Toolとして公開する
mcp.tool()(get_current_time)


if __name__ == "__main__":
    mcp.run()
