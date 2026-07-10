import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from tools import get_current_time

load_dotenv()

MODEL = "gemma-4-31b-it"

# Gemini APIのキーを使って、OpenAIクライアントを初期化
# base_urlをGemini APIのOpenAI互換エンドポイントに向ける
client = OpenAI(
    api_key=os.environ["GEMINI_API_KEY"],
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

LOCAL_FUNCTIONS = {
    "get_current_time": get_current_time,
}

# OpenAIフォーマットでのツール定義
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "現在の日時を取得する。"
        }
    }
]

def main():
    messages = []
    print("Gemma 4 Tool Use デモ（終了するには exit）")
    
    while True:
        user_input = input("あなた: ")
        if user_input.strip() in ("exit", "quit"):
            break

        messages.append({"role": "user", "content": user_input})

        while True:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
            )
            
            message = response.choices[0].message
            messages.append(message)

            # ツール呼び出しがない場合は回答を表示して終了
            if not message.tool_calls:
                print(f"Gemma: {message.content}")
                break

            # ツール呼び出しがある場合の処理
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                
                # 引数がある場合はパースする
                args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                
                func = LOCAL_FUNCTIONS.get(func_name)
                if func:
                    result = func(**args)
                else:
                    result = f"Error: Function {func_name} not found"

                # 実行結果をメッセージ履歴に追加
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": str(result)
                })

if __name__ == "__main__":
    main()