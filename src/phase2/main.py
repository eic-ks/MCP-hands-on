# phase2のCLIベースでやり取りするバージョン
import asyncio
import sys
from pathlib import Path

# 親ディレクトリ（src）を検索パスに追加
sys.path.append(str(Path(__file__).parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from utils.llm_client import create_client
from client import mcp_tools_to_openai_schema

SERVER_SCRIPT = str(Path(__file__).parent / "server.py")

async def main():
    from agent import run_turn  # agentとの循環インポートを避けるため呼び出し時に遅延インポート

    client = create_client()
    params = StdioServerParameters(command=sys.executable, args=[SERVER_SCRIPT])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Tool Discovery: サーバーが公開するTool一覧を取得し、その場でスキーマに変換する（手書きしない）
            tools_result = await session.list_tools()
            tools = mcp_tools_to_openai_schema(tools_result.tools)

            messages: list = []
            print("Gemma Tool Use デモ（スキーマ・実行ともMCPサーバー経由・終了するには exit）")

            while True:
                user_input = input("あなた: ")
                if user_input.strip() in ("exit", "quit"):
                    break

                messages.append({"role": "user", "content": user_input})
                await run_turn(session, client, tools, messages)

                print(f"Gemma: {messages[-1].content}")


if __name__ == "__main__":
    asyncio.run(main())
