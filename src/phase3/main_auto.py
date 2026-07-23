# phase3のCLIベースでやり取りするバージョン（自動連携: google-genai SDKにMCPセッションを直接渡す）
#
# main.py（手動実装）との違いはここだけ：
#   - Tool Schema変換（mcp_tools_to_gemini_schema）を書かない
#   - Function Callの実行ループ（agent.run_turn / call_mcp_tool）を書かない
#   - config.tools に生のClientSessionをそのまま渡し、SDK内部のAFC(Automatic Function Calling)に
#     Tool Discovery(list_tools)とTool実行(call_tool)を任せる
#
# 注意点:
#   - この自動連携はSDK内部で非同期処理（await session.list_tools()等）を行うため、
#     同期クライアント(client.models)ではなく非同期クライアント(client.aio.models)が必須。
#   - AFCは複数ターンのFunction Callを内部でループして最終応答まで自動で進めるが、
#     途中経過（function_call/function_response）は response.automatic_function_calling_history
#     に入る。次ターンの会話履歴を保つには、これを使ってcontentsを組み立て直す必要がある。
#   - configは`types.GenerateContentConfig(tools=[session])`ではなくdictで渡す。
#     GenerateContentConfigインスタンスを渡すとSDK内部で`config.model_copy(deep=True)`が
#     ClientSessionをRawで含んだまま実行され、内部のasyncio Futureがpickle不可でクラッシュする
#     （google-genai 2.11.0時点のバグ）。dictならその場でモデルを新規構築するだけなので発生しない。
import asyncio
import sys
from pathlib import Path

# 親ディレクトリ（src）を検索パスに追加
sys.path.append(str(Path(__file__).parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google.genai import types

from utils.llm_client import create_gemini_client, GEMINI_MODEL
from client import SERVER_SCRIPT


async def main():
    client = create_gemini_client()
    params = StdioServerParameters(command=sys.executable, args=[SERVER_SCRIPT])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 生のClientSessionをそのままtoolsに渡す。
            # list_tools()による変換もcall_tool()の実行もSDKが自動でやってくれる。
            config = {"tools": [session]}

            contents: list[types.Content] = []
            print("Gemini Tool Use デモ（自動連携・終了するには exit）")

            while True:
                user_input = input("あなた: ")
                if user_input.strip() in ("exit", "quit"):
                    break

                contents.append(types.Content(role="user", parts=[types.Part(text=user_input)]))

                response = await client.aio.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=contents,
                    config=config,
                )

                # Function Callが発生していればautomatic_function_calling_historyに
                # 呼び出し/結果を含む全履歴が入っているので、それを次ターンの土台にする。
                history = response.automatic_function_calling_history
                if history:
                    contents = list(history)
                contents.append(response.candidates[0].content)

                print(f"Gemini: {response.text}")


if __name__ == "__main__":
    asyncio.run(main())
