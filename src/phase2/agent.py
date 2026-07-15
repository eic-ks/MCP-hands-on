from openai import OpenAI
import sys
from pathlib import Path
from mcp import ClientSession


# 親ディレクトリ（src）を検索パスに追加
sys.path.append(str(Path(__file__).parent.parent))

from utils.llm_client import MODEL
from client import call_mcp_tool


async def run_turn(
    session: ClientSession, client: OpenAI, tools: list[dict], messages: list, max_tool_use: int = 3
) -> None:
    """最終回答が出るまでツール呼び出しを繰り返し、messagesに追記する。
    ツールを呼ぶかどうかの判断のみを担い、実行そのものはMCPクライアント（call_mcp_tool）に委譲する。"""
    while max_tool_use > 0:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
        )

        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            return

        for tool_call in message.tool_calls:
            result = await call_mcp_tool(session, tool_call.function.name, tool_call.function.arguments)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": result,
                }
            )

        max_tool_use -= 1
