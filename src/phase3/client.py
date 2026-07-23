import asyncio
import sys
import threading
from pathlib import Path

# 親ディレクトリ（src）を検索パスに追加
sys.path.append(str(Path(__file__).parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool as MCPTool
from google import genai
from google.genai import types

SERVER_SCRIPT = str(Path(__file__).parent / "server.py")


def mcp_tools_to_gemini_schema(tools: list[MCPTool]) -> types.Tool:
    """tools/listで取得したMCPのTool定義を、Gemini SDKのtypes.Toolへ変換する。
    inputSchema(JSON Schema)はparameters_json_schemaへそのまま渡せる。"""
    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name=tool.name,
                description=tool.description or "",
                parameters_json_schema=tool.inputSchema,
            )
            for tool in tools
        ]
    )


async def call_mcp_tool(session: ClientSession, function_call: types.FunctionCall) -> types.Part:
    """GeminiのFunctionCallを、MCPサーバーへのtools/callに変換して実行する。"""
    args = function_call.args if function_call.args else {}
    result = await session.call_tool(function_call.name, args)
    text = "\n".join(block.text for block in result.content if hasattr(block, "text"))
    return types.Part.from_function_response(
        name=function_call.name,
        response={"result": text},
    )


class McpSession:
    """Streamlitのように画面操作のたびにスクリプトが再実行される環境向けのラッパー。

    stdio_client/ClientSessionが内部で使うanyioのtask group(cancel scope)は
    「開いたのと同じTaskで閉じる」必要があるため、専用スレッド上の1つのコルーチンで
    接続を開いたまま維持し続け、tool call等はasyncio.run_coroutine_threadsafeで
    そのコルーチンと同じイベントループ上に投げ込んで実行する。（phase2と同じ設計）
    """

    def __init__(self) -> None:
        self.tools: types.Tool | None = None
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
                self.tools = mcp_tools_to_gemini_schema(tools_result.tools)
                self._ready.set()

                await self._stop_event.wait()  # close()が呼ばれるまでセッションを維持し続ける

    def run_turn(self, client: genai.Client, contents: list[types.Content], max_tool_use: int = 3) -> None:
        """agentのrun_turnを、セッションを維持しているイベントループ上で同期的に実行する。"""
        from agent import run_turn  # agentとの循環インポートを避けるため呼び出し時に遅延インポート

        coro = run_turn(self._session, client, self.tools, contents, max_tool_use)
        asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def close(self) -> None:
        """MCPセッション（サーバー子プロセスを含む）とスレッドを終了する。"""
        if self._stop_event is not None:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        self._thread.join(timeout=5)
        self._loop.close()
