import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from tools import get_current_time

load_dotenv()

# google.genaiがサポートするモデルはGeminiシリーズのみで現時点ではオープンモデル非対応
MODEL = "gemma-4-31b-it"

# ローカル関数名 -> 実体 のマッピング（Gemini から関数名で呼ばれたときに引く）
LOCAL_FUNCTIONS = {
    "get_current_time": get_current_time,
}

TOOLS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="get_current_time",
            description="現在の日時を取得する。",
        ),
    ]
)

CONFIG = types.GenerateContentConfig(tools=[TOOLS])


def call_local_function(function_call: types.FunctionCall) -> types.Part:
    func = LOCAL_FUNCTIONS[function_call.name]
    # argsが存在する場合は辞書を展開してキーワード引数として渡す
    kwargs = function_call.args if function_call.args else {}
    result = func(**kwargs)
    return types.Part.from_function_response(
        name=function_call.name,
        response={"result": result},
    )


def main():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    contents: list[types.Content] = []

    print("Gemini Tool Use デモ（終了するには exit）")
    while True:
        user_input = input("あなた: ")
        if user_input.strip() in ("exit", "quit"):
            break

        contents.append(types.Content(role="user", parts=[types.Part(text=user_input)]))

        while True:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=CONFIG,
            )
            model_content = response.candidates[0].content
            contents.append(model_content)

            function_calls = [
                part.function_call for part in model_content.parts if part.function_call
            ]
            if not function_calls:
                print(f"Gemini: {response.text}")
                break

            function_response_parts = [
                call_local_function(function_call) for function_call in function_calls
            ]
            contents.append(types.Content(role="user", parts=function_response_parts))


if __name__ == "__main__":
    main()
