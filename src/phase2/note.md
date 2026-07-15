# フェーズを通じた学び

## Phase1→Phase2: MCP導入によるAgentの役割変化

Phase1では、agentが「ツールを呼ぶか判断する」「ツールのスキーマを知っている」「ツールを実行する」の3つを一手に担っていた。

```python
# phase1/agent.py
from utils.tools import LOCAL_FUNCTIONS, TOOLS  # スキーマも実装もagentが直接知っている

def call_local_function(name, arguments):
    func = LOCAL_FUNCTIONS.get(name)  # 実行そのものもagentの中で完結
    ...

def run_turn(client, messages, MaxToolUse=3):
    response = client.chat.completions.create(..., tools=TOOLS)  # 手書きスキーマ
    ...
    result = call_local_function(tool_call.function.name, tool_call.function.arguments)
```

Phase2ではMCPサーバー・MCPクライアントを挟むことで、3つの責務が別々のファイルに分かれた。

- **server.py（MCPサーバー）**: ツールの実装を持ち、MCPプロトコルで公開する（`mcp.tool()(get_current_time)`）。関数のシグネチャ・docstringからスキーマが自動生成されるため、**手書きの`TOOLS`が不要になった。**
- **client.py（MCPクライアント）**: サーバーとの接続管理、Tool Discovery（`list_tools()` → `mcp_tools_to_openai_schema()`でOpenAI形式へ変換）、ツール実行の変換（`call_mcp_tool`: LLMの関数呼び出し引数を`session.call_tool()`に渡し、結果をテキストに戻す）を担当。「MCPの配線」を知っているのはここだけ。
- **agent.py（Agent）**: LLMの応答を見て「ツールを呼ぶか、最終回答を返すか」だけを判断する。ツールの実装がローカル関数なのかMCPサーバー経由なのかは知らず、実行は外から渡された`call_mcp_tool`に委譲する。

```python
# phase2/agent.py
from client import call_mcp_tool  # 実行方法の詳細は知らず、呼び出し口だけを知っている

async def run_turn(session, client, tools, messages, max_tool_use=3):
    response = client.chat.completions.create(..., tools=tools)  # スキーマは外から渡される
    ...
    result = await call_mcp_tool(session, tool_call.function.name, tool_call.function.arguments)
```

つまりMCP導入によって、agentは「ツール実行の詳細（ローカル関数か、別プロセスのMCPサーバーか）」から切り離され、ツール利用の意思決定ロジックだけを持つ薄い層になった。ツールのスキーマも、agentが手書きするものから、MCPサーバーが公開する情報を都度取得する形に変わった（Single Source of Truthがコード上の定数からMCPサーバー自身に移った）。

副次的な変化として、ツール実行がstdio経由の別プロセス呼び出しになったため`run_turn`は同期関数から非同期関数（`async def`）になり、呼び出し側も`ClientSession`と（一度だけDiscoveryした）`tools`スキーマを渡す必要が生じた。

### Tool Schemaの自動作成について
- descriptionは流石に自動生成ではない。

```python
# 書き方はいくつかある

# phase2/server.py
mcp.tool()(get_current_time)
# utils/tools.py
def get_current_time() -> str:
    """現在の日時を取得する。"""　#ここが読み取られてdescriptionになる
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# phase2/server.py
mcp.tool(description="現在の日時を取得する。")(get_current_time)#直接指定も可能


# phase2/server.py
@mcp.tool
def get_current_time() -> str:
    """現在の日時を取得する。"""　#ここが読み取られてdescriptionになる
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# server.py内に関数定義を記述し、mcp.tool()()を使わずにデコレータを使用して登録する方法もある
```

### MCP Inspector
- ブラウザからGUIでMCPサーバー単体で機能を試せる
```bash
uv run mcp dev src/phase2/server.py
```

### 循環インポートの回避
`agent.py`は`client.py`の`call_mcp_tool`をトップレベルでインポートする。逆に`client.py`は`agent.py`の`run_turn`を、実際に呼び出す関数（`McpSession.run_turn`やCLIの`main()`）の中で遅延インポートしている。これは、その時点で両モジュールのロードが完了しているため、モジュールロード時の循環参照を避けられるため。

## MCPセッションとは何か

MCPセッション＝MCPクライアントとMCPサーバー間の通信路のこと。今回採用したstdio transportでは、`stdio_client()`がサーバー（`server.py`）を**子プロセスとして起動**し、標準入出力のパイプでJSON-RPCをやり取りする。その上で`ClientSession`が`initialize`ハンドシェイク（プロトコルバージョン・機能のネゴシエーション）を行い、以降`list_tools()`や`call_tool()`が呼べる状態になる。

重要なのは、**tool callのたびにセッションを張り直すわけではない**という点。`initialize`のコストや、stdioの場合は「セッションを閉じる＝サーバーの子プロセスを終了させる」ことを考えると、一度確立したセッションを複数ターン・複数tool callにわたって使い回すのがMCPの自然な使い方。`client.py`の`main()`（CLI版）も、Phase2で作った`McpSession`（Streamlit版）も、セッション確立は1回だけ行い、以降使い回す設計になっている。

## MCPの2つのtransport: stdio vs Streamable HTTP

- **stdio（今回採用）**: クライアントがサーバーを子プロセスとして起動する。サーバーはポートを開かず、標準入出力を読み書きするだけ。ライフサイクルはクライアント（を起動したホストアプリ）側が握る。Claude Desktop/Claude Codeが設定ファイルの`command`/`args`を見て、起動時に各MCPサーバーを子プロセスとして立ち上げるのがこのパターン。ローカル・単一クライアントの学習用途に手軽。
- **Streamable HTTP（旧SSE）**: サーバーが独立したプロセスとして自分でポートを開いて起動しておき、クライアントはHTTPでアクセスする。サーバーのライフサイクルはサーバー自身が握り、リモートホストや複数クライアントからの接続が可能。「サーバーを手動で起動しておいて、そこにクライアントがリクエストを送る」という一般的なクライアント/サーバーのイメージはこちらに近い。

Phase2ではローカル学習用にstdioを選んでいるが、リモートサーバーに繋ぐ場合や複数クライアントで共有する場合はStreamable HTTPを使うことになる。

## Streamlitでセッションを維持する難しさ（app.py）

Streamlitは操作のたびにスクリプト全体を1行目から再実行するモデルなので、CLI版のように`async with stdio_client(...): async with ClientSession(...): while True: ...`とwhileループの中にセッションを持ち続ける書き方がそのまま使えない（スクリプトの実行が終わるたびに`async with`のブロックを抜けてセッションが閉じてしまう）。そこで`st.session_state`にセッションを保持し、rerunをまたいで使い回す必要がある。

最初に試したのは、`AsyncExitStack`で`stdio_client`/`ClientSession`を手動で`enter_async_context`し、`loop.run_until_complete()`を呼ぶたびに開いたり閉じたりする方式だった。しかしこれは**閉じる際に例外になった**（実測）。

```
RuntimeError: Attempted to exit cancel scope in a different task than it was entered in
```

原因は、MCP SDKの内部で使われているanyioのtask group（cancel scope）が「開いたのと同じasyncio Taskの中で閉じる」ことを要求する構造的並行性（structured concurrency）のルールを持っているため。`run_until_complete()`を呼ぶたびに新しいTaskが作られるので、「確立時のTask」と「クローズ時のTask」が別物になってしまい、このルールに違反していた。

解決策として`McpSession`クラス（`client.py`）を用意し、専用スレッド上で1つの長寿命コルーチン（`_serve()`）を回し続ける方式にした。

- `_serve()`は`async with stdio_client(...): async with ClientSession(...): ...`を開いたまま、`asyncio.Event`（`_stop_event`）が立つまで`await`で待機し続ける。つまり**接続の開始と終了が同じコルーチン（同じTask）の中で完結する**。
- 外部（Streamlitのメインスレッド）からtool callやrun_turnを実行したいときは、`asyncio.run_coroutine_threadsafe(coro, self._loop)`でこの専用ループに処理を投げ込む。これは新しいTaskとして実行されるが、cancel scopeのenter/exitには関与しないため問題にならない。
- `close()`は`_stop_event`をセットして`_serve()`の待機を解除し、同じコルーチンの中で`async with`ブロックを正しい順序で抜けさせる（＝サーバー子プロセスも含めて確実に終了する）。

この設計により、`app.py`側は`st.session_state.mcp = McpSession()`と`st.session_state.mcp.run_turn(client, messages)`を呼ぶだけのシンプルな形を維持でき、`atexit.register(st.session_state.mcp.close)`でプロセス終了時にサーバー子プロセスの後始末も保証できる。

**学びの要点**: 非同期リソース（特にanyio/MCP SDKのように構造化並行性を使うライブラリ）を、Streamlitのような「同期コードから断続的に呼ばれる」フレームワークにまたがって長生きさせたい場合、単純に`run_until_complete`を都度呼ぶだけでは破綻することがある。「リソースの開始〜終了を同じコルーチン・同じイベントループの中で完結させ、外部からの利用は別Taskとしてそのループに投げ込む」という設計（専用スレッド＋長寿命コルーチン＋`run_coroutine_threadsafe`）が定石になる。
