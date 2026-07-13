import json

from openai import OpenAI

from llm_client import MODEL
from tools import LOCAL_FUNCTIONS, TOOLS


def call_local_function(name: str, arguments: str) -> str:
    args = json.loads(arguments) if arguments else {}
    func = LOCAL_FUNCTIONS.get(name)
    if func is None:
        return f"Error: Function {name} not found"
    return str(func(**args))


def run_turn(client: OpenAI, messages: list) -> None:
    """最終回答が出るまでツール呼び出しを繰り返し、messagesに追記する。UIには依存しない。"""
    while True:
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
