# フェーズを通じた学び

## Phase2→Phase3で何が変わり、何が変わらなかったか

Phase3の題材は「素のGemini SDK（`google-genai`）からMCPサーバーを利用する」。
Phase2はOpenAI互換クライアント（Gemma向け）からMCPサーバーを利用していたので、
**サーバー側（Tool実装・公開）は一切変えず、クライアント側（SDKとの橋渡し）だけを作り直す**のがPhase3の本質。

結果として：

- **変わらなかったもの**: `server.py`（1文字も違わない）、`McpSession`のセッション管理設計、MCP自体の通信（`list_tools()` / `call_tool()`）
- **変わったもの**: Tool Schemaの表現形式、Function Callの引数の型、会話履歴のデータモデル、レスポンスの取り出し方、Gemini SDKを使用する関係上、Geminiシリーズを使う必要があった（Thinkingしないのでテキストの整形が不要）

この「変わらなかったもの」と「変わったもの」の境界線こそが、MCPが標準化している範囲（サーバーとの通信プロトコル）と、SDKごとに違う範囲（LLMベンダーのAPI仕様）の境界線そのもの。

## server.pyが1文字も変わらないという事実

```python
# phase2/server.py と phase3/server.py は完全に同一
mcp.tool()(get_current_time)
```

MCPサーバーは「どのSDK・どのモデルからアクセスされるか」を一切知らないし、知る必要もない。
Tool Discovery（`tools/list`）とTool実行（`tools/call`）というJSON-RPCベースのプロトコルさえ守っていれば、
クライアント側がOpenAI互換SDKだろうがGemini nativeのSDKだろうが同じサーバーに接続できる。
これがMCPの核心的な価値（「N個のSDK × M個のToolの組み合わせ爆発を防ぐ」）を最も端的に示している箇所。

## Tool Schema変換：情報源は同じ、包み方だけがSDKごとに違う

MCPサーバーが公開する`inputSchema`（JSON Schema形式）は共通の単一の情報源。ただし、それをLLMに渡す「容器」の形がSDKごとに異なる。

```python
# phase2/client.py: OpenAI互換 → dictのリスト（Tool 1つにつき1 dict）
def mcp_tools_to_openai_schema(tools: list[MCPTool]) -> list[dict]:
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

# phase3/client.py: Gemini native → types.Tool 1つ（function_declarationsにまとめる）
def mcp_tools_to_gemini_schema(tools: list[MCPTool]) -> types.Tool:
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
```

- OpenAI互換: `tools`は「1関数=1 dict」のフラットなリスト
- Gemini native: `tools`は「1つの`types.Tool`が複数の`FunctionDeclaration`を束ねる」入れ子構造
- どちらも`tool.inputSchema`（生のJSON Schema）をほぼそのまま渡せる。Gemini SDK側は`parameters`（Schema型への厳密な変換が必要）と`parameters_json_schema`（JSON Schemaを直接渡せる）の2種類のフィールドを持っており、後者を使うことでMCPの`inputSchema`をそのまま横流しできた。

## Function Callの引数：JSON文字列 vs パース済みdict

```python
# phase2/client.py: OpenAIは引数をJSON文字列で返すため、自分でパースする必要がある
async def call_mcp_tool(session: ClientSession, name: str, arguments: str) -> str:
    args = json.loads(arguments) if arguments else {}
    result = await session.call_tool(name, args)
    ...

# phase3/client.py: Geminiは引数をパース済みのdictで返す
async def call_mcp_tool(session: ClientSession, function_call: types.FunctionCall) -> types.Part:
    args = function_call.args if function_call.args else {}
    result = await session.call_tool(function_call.name, args)
    ...
```

地味だが、SDKごとにレスポンスの「生データ度合い」が違う典型例。OpenAI互換は関数呼び出し引数をJSON文字列のまま返す（＝パースはクライアント側の責任）のに対し、Gemini SDKは`FunctionCall.args`としてすでにdictにパースしてくれている。

## 会話履歴のデータモデル：フラットな`messages` vs 構造化された`Content`/`Part`

```python
# phase2/agent.py: OpenAI形式。role="tool" という専用の役割があり、
# tool_call_id で「どの呼び出しに対する結果か」を明示的に紐付ける
messages.append({
    "role": "tool",
    "tool_call_id": tool_call.id,
    "name": tool_call.function.name,
    "content": result,
})

# phase3/agent.py: Gemini形式。"tool" という役割は存在せず、
# function_call / function_response は user/model の Content の中の Part として埋め込まれる。
# 呼び出しと結果の対応は明示的なIDではなく「隣接するContentの順序」で決まる
contents.append(types.Content(role="user", parts=function_response_parts))
```

- OpenAI形式は「role」が会話のフラットな配列を作り、`tool`という第3の役割で関数結果を表現する。呼び出しと結果は`tool_call_id`で明示的に紐付く。
- Gemini形式には`tool`ロールが無く、`user`/`model`の2ロールのみ。関数呼び出し（`function_call`）はmodelのContentの中のPartとして、その結果（`function_response`）は次のuserのContentの中のPartとして現れる。対応関係はIDではなく「隣り合った順序」で暗黙的に決まる。
- この違いはStreamlit UIの描画コード（`app.py`）にも直結した。phase2の`render_message`はトップレベルの`role`だけを見て分岐すればよかったが、phase3の`render_content`は`Content`の中の各`Part`の種類（`text` / `function_call` / `function_response`）を見て分岐する必要があった。

## レスポンスの取り出し方の違い

```python
# phase2: response.choices[0].message
# phase3: response.candidates[0].content
```

OpenAI互換は`choices`（候補の配列）の中に`message`、Gemini nativeは`candidates`（候補の配列）の中に`content`。「候補が複数返りうる」という発想自体は共通しているが、命名も構造も微妙に異なる。

## McpSession（Streamlitセッション管理）は変わらなかった

`McpSession`クラス（専用スレッド＋長寿命コルーチン＋`asyncio.run_coroutine_threadsafe`という設計）は、phase2からほぼそのまま移植できた。変わったのは`self.tools`の型（`list[dict]` → `types.Tool`）と`run_turn`に渡す引数名（`messages` → `contents`）程度。

これは、この設計が解決している問題（anyioのtask group/cancel scopeを「開いたのと同じTaskで閉じる」必要がある、というstdio transport由来の構造的制約）が、**LLM SDKの種類とは無関係にMCPクライアント側だけに閉じた問題だから**。SDKを差し替えても、MCPとの接続ライフサイクル管理は影響を受けない。

## つまずいた点：モデル名の陳腐化（MCPとは無関係の実務的な注意）

実装当初`phase1/sub.py`にならって`gemini-2.5-flash-lite`を使ったところ、
`404 This model models/gemini-2.5-flash-lite is no longer available to new users` で失敗した
（`client.models.list()`には出てくるのに、新規ユーザーには使えないという状態）。
`gemini-flash-lite-latest`に変更して解決。MCPやSDK設計とは無関係だが、モデル名は変わりうるので動かない時はまず`client.models.list()`で使えるモデルを確認するとよい。

## 発展：google-genai SDKのMCP自動連携を実装して検証した（`main_auto.py`）

`mcp_tools_to_gemini_schema`での変換や`call_mcp_tool`での手動実行は、理解のためにあえて手で書いたものだった。
本当にやりたかったのは「SDKとMCPサーバーを直接繋げる」ことそのものだったので、`google-genai`SDKが持つ自動連携機能を`main_auto.py`として別途実装し、手動実装と並べて動かせるようにした。

```python
# main.py（手動）: 変換・実行ループをすべて自前で書く
tools = mcp_tools_to_gemini_schema(tools_result.tools)
await run_turn(session, client, tools, contents)  # 内部でcall_mcp_toolを呼ぶ

# main_auto.py（自動）: 生のClientSessionをtoolsに渡すだけ
config = {"tools": [session]}
response = await client.aio.models.generate_content(model=GEMINI_MODEL, contents=contents, config=config)
```

`config.tools`に生の`mcp.ClientSession`を渡すと、SDK内部（`_extra_utils.parse_config_for_mcp_sessions`）が`await session.list_tools()`でTool Discoveryを行い、`types.Tool`への変換（`_mcp_utils.mcp_to_gemini_tool`）まで自動でやってくれる。さらにAFC（Automatic Function Calling）が、Function Callが返る限り`call_tool()`の実行とモデルへの再送信を内部でループし続け、最終的なテキスト応答が出るまで人間側は1回`generate_content`を呼ぶだけでよい。中身を読むと、変換ロジックもFunction Call実行ロジックも、今回手で`client.py`に書いたものとほぼ同じことをしているだけだとわかり、「自動化＝ブラックボックス」ではなく「自分で書いたものが内部化されただけ」だと確認できた。

自動連携ならではの制約や罠も見つかった：

- **非同期クライアント必須**: `parse_config_for_mcp_sessions`が`await`を含む非同期関数のため、`client.models.generate_content`（同期）ではなく`client.aio.models.generate_content`を使う必要がある。
- **configはdictで渡す**: `types.GenerateContentConfig(tools=[session])`のようにオブジェクトとして渡すと、SDK内部で実行される`config.model_copy(deep=True)`が生の`ClientSession`ごとdeepcopyしようとし、内部の`asyncio.Future`がpickle不可のため`TypeError: cannot pickle '_asyncio.Future' object`でクラッシュする（`google-genai==2.11.0`時点のバグ）。`config = {"tools": [session]}`のようにdictで渡せば、SDKがその場で`GenerateContentConfig`を新規構築するだけでdeepcopyを経由しないため回避できる。
- **複数ターンの会話履歴の再構築**: AFCのループ途中経過（`function_call`/`function_response`のPart）はレスポンス自体には残らず、`response.automatic_function_calling_history`という別フィールドに入る。次ターンのために`contents`を維持するには、Function Callが発生したターンでは`automatic_function_calling_history`を土台にし、発生しなかったターンでは元の`contents`をそのまま使う、という分岐が必要だった。

### OpenAI互換SDK（Phase2）には同種の自動連携はない

`openai`パッケージ（`openai==2.45.0`）のソースを見ると、`ClientSession`や`mcp.client`への参照は一切なく、あるのは`mcp_call` / `mcp_list_tools`といったイベント型定義（`openai/types/responses/`, `openai/types/realtime/`）だけだった。これらはChat Completions APIではなく**Responses API**（`client.responses.create`）向けの「Remote MCP」という別機能のためのもので、仕組みがgoogle-genaiとは根本的に異なる。

- **google-genai（クライアント側統合）**: 手元の`ClientSession`（stdio経由でローカルsubprocessに接続）をSDKにそのまま渡すと、**自分のプロセス**がTool Discovery/実行を行う。
- **OpenAI Remote MCP（サーバー側統合）**: `{"type": "mcp", "server_url": "https://...", "server_label": "..."}`をtoolsに指定すると、**OpenAIのサーバー自身**がそのURLへ接続してTool Discovery/実行を行い、結果を`mcp_call`イベントとしてストリームで返す。ローカルの`ClientSession`オブジェクトを渡す口はSDKに存在しない。

このプロジェクトの構成には2点で噛み合わない:

1. `server.py`は**stdio transport**（ローカルsubprocess）なのに対し、OpenAI Remote MCPは公開HTTP(S)経由のMCPサーバーを要求する。そのままでは使えず、サーバーをHTTP化して外部にホストする必要がある。
2. Phase2はGeminiの**OpenAI互換エンドポイント**（Chat Completions相当）を使っている。Remote MCPはOpenAI固有のResponses APIの機能であり、Gemini側の互換レイヤーがそれを実装しているかは未検証（実装していない可能性が高い）。

つまりPhase2で採用した「手動連携」は、単なる選択肢の1つではなく、OpenAI系SDKで現実的に選べる**唯一**の連携方法だった、という位置づけになる。

## Phase3で得られた結論

Phase1→Phase2→Phase3を通して見ると：

- Phase1: Tool実装・スキーマ・実行判断のすべてを1つのSDKが密結合で担っていた
- Phase2: Tool実装をMCPサーバーへ切り出した。ただしSDKはOpenAI互換のまま
- Phase3: **SDKをGemini nativeに差し替えても、サーバー側は無傷だった**

つまりMCPは「Tool実装とTool利用（SDK/モデル）を疎結合にする」ためのレイヤーとして機能しており、
差し替えが必要だったのは常に「クライアント側のSDKごとの流儀に合わせる変換・ループ部分」（`client.py`の変換関数、`agent.py`のループ、`app.py`の描画）だけだった。

さらに`main_auto.py`でSDK自動連携を実装したことで、この「変換・ループ部分」自体もMCPプロトコルの外側（＝SDKベンダーの実装詳細）であることがもう一段明確になった。`server.py`もMCPの通信仕様（`tools/list`・`tools/call`）も変えずに、クライアント側の「変換・ループを自分で書くか、SDKに委譲するか」だけを選べる。これは「SDKとMCPサーバーを直接繋げる」という当初の狙いが、単なる思いつきではなく実装レベルで再現可能だったことの裏付けになった。
これで README の「MCPはFunction Callingを標準化したインターフェースである」というテーゼが、実装レベルで裏付けられた。
