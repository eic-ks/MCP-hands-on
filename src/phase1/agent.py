import json

from openai import OpenAI
import sys
from pathlib import Path

# 親ディレクトリ（src）を検索パスに追加
sys.path.append(str(Path(__file__).parent.parent))

from utils.llm_client import MODEL
from utils.tools import LOCAL_FUNCTIONS, TOOLS


def call_local_function(name: str, arguments: str) -> str:
    args = json.loads(arguments) if arguments else {}
    func = LOCAL_FUNCTIONS.get(name)
    if func is None:
        return f"Error: Function {name} not found"
    return str(func(**args))


def run_turn(client: OpenAI, messages: list, MaxToolUse: int = 3) -> None:
    """最終回答が出るまでツール呼び出しを繰り返し、messagesに追記する。UIには依存しない。"""
    while MaxToolUse > 0:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
        )

        message = response.choices[0].message
        messages.append(message)

        # ツール呼び出しがない場合は最終回答なので終了
        if not message.tool_calls:
            return

        for tool_call in message.tool_calls:
            result = call_local_function(tool_call.function.name, tool_call.function.arguments)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": result,
                }
            )
        
        MaxToolUse -= 1
