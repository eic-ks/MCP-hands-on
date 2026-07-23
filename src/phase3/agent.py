import sys
from pathlib import Path

# 親ディレクトリ（src）を検索パスに追加
sys.path.append(str(Path(__file__).parent.parent))

from google import genai
from google.genai import types
from mcp import ClientSession

from utils.llm_client import GEMINI_MODEL
from client import call_mcp_tool


async def run_turn(
    session: ClientSession,
    client: genai.Client,
    tools: types.Tool,
    contents: list[types.Content],
    max_tool_use: int = 3,
) -> None:
    """最終回答が出るまでツール呼び出しを繰り返し、contentsに追記する。
    ツールを呼ぶかどうかの判断のみを担い、実行そのものはMCPクライアント（call_mcp_tool）に委譲する。"""
    config = types.GenerateContentConfig(tools=[tools])

    while max_tool_use > 0:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=config,
        )
        model_content = response.candidates[0].content
        contents.append(model_content)

        function_calls = [part.function_call for part in model_content.parts if part.function_call]
        if not function_calls:
            return

        function_response_parts = [
            await call_mcp_tool(session, function_call) for function_call in function_calls
        ]
        contents.append(types.Content(role="user", parts=function_response_parts))

        max_tool_use -= 1
