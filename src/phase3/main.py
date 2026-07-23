# phase3のCLIベースでやり取りするバージョン（素のGemini SDK + MCP Client）
import asyncio
import sys
from pathlib import Path

# 親ディレクトリ（src）を検索パスに追加
sys.path.append(str(Path(__file__).parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google.genai import types

from utils.llm_client import create_gemini_client
from client import mcp_tools_to_gemini_schema, SERVER_SCRIPT


async def main():
    from agent import run_turn  # agentとの循環インポートを避けるため呼び出し時に遅延インポート

    client = create_gemini_client()
    params = StdioServerParameters(command=sys.executable, args=[SERVER_SCRIPT])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Tool Discovery: サーバーが公開するTool一覧を取得し、その場でGemini形式に変換する
            tools_result = await session.list_tools()
            tools = mcp_tools_to_gemini_schema(tools_result.tools)

            contents: list[types.Content] = []
            print("Gemini Tool Use デモ（素のSDK・MCPサーバー経由・終了するには exit）")

            while True:
                user_input = input("あなた: ")
                if user_input.strip() in ("exit", "quit"):
                    break

                contents.append(types.Content(role="user", parts=[types.Part(text=user_input)]))
                await run_turn(session, client, tools, contents)

                print(f"Gemini: {contents[-1].parts[0].text}")


if __name__ == "__main__":
    asyncio.run(main())
