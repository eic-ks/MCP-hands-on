import asyncio
import json
import sys
import threading
from pathlib import Path

# 親ディレクトリ（src）を検索パスに追加
sys.path.append(str(Path(__file__).parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool as MCPTool

from utils.llm_client import create_client

SERVER_SCRIPT = str(Path(__file__).parent / "server.py")


def mcp_tools_to_openai_schema(tools: list[MCPTool]) -> list[dict]:
    """tools/listで取得したMCPのTool定義を、OpenAIのFunction Callingスキーマへ変換する。
    手書きのTOOLSは不要になり、MCPサーバーが公開しているTool一覧がそのままスキーマの単一の情報源になる。"""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            },
        }
        for tool in tools
    ]


async def call_mcp_tool(session: ClientSession, name: str, arguments: str) -> str:
    """LLMからのFunction Call引数を、MCPサーバーへのtools/callに変換して実行する。"""
    args = json.loads(arguments) if arguments else {}
    result = await session.call_tool(name, args)
    return "\n".join(block.text for block in result.content if hasattr(block, "text"))


class McpSession:
    """Streamlitのように画面操作のたびにスクリプトが再実行される環境向けのラッパー。

    stdio_client/ClientSessionが内部で使うanyioのtask group(cancel scope)は
    「開いたのと同じTaskで閉じる」必要があるため、専用スレッド上の1つのコルーチンで
    接続を開いたまま維持し続け、tool call等はasyncio.run_coroutine_threadsafeで
    そのコルーチンと同じイベントループ上に投げ込んで実行する。
    """

    def __init__(self) -> None:
        self.tools: list[dict] = []
        self._loop = asyncio.new_event_loop()
        self._session: ClientSession | None = None
        self._stop_event: asyncio.Event | None = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._ready.wait()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())

    async def _serve(self) -> None:
        self._stop_event = asyncio.Event()
        params = StdioServerParameters(command=sys.executable, args=[SERVER_SCRIPT])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools_result = await session.list_tools()
                self._session = session
                self.tools = mcp_tools_to_openai_schema(tools_result.tools)
                self._ready.set()

                await self._stop_event.wait()  # close()が呼ばれるまでセッションを維持し続ける

    def run_turn(self, client, messages: list, max_tool_use: int = 3) -> None:
        """agentのrun_turnを、セッションを維持しているイベントループ上で同期的に実行する。"""
        from agent import run_turn  # agentとの循環インポートを避けるため呼び出し時に遅延インポート

        coro = run_turn(self._session, client, self.tools, messages, max_tool_use)
        asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def close(self) -> None:
        """MCPセッション（サーバー子プロセスを含む）とスレッドを終了する。"""
        if self._stop_event is not None:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        self._thread.join(timeout=5)
        self._loop.close()


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
