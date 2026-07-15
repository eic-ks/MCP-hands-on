# プロジェクトを通じた学び

## load_dotenv()
- Parse a .env file and then load all the variables found as environment variables.

## types(google.genai)
- APIで送受信するJSONを型付きクラスで表現する（オブジェクトを書くとSDKがJSONへ変換してくれるのでJSONを書かなくてよくなる）

        ''''
        {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": "東京の天気は？"
                        }
                    ]
                }
            ],
            "tools": [
                {
                    "functionDeclarations": [
                        {
                            "name": "get_weather",
                            "description": "天気を取得する",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "city": {
                                        "type": "string"
                                    }
                                }
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1000
            }
        }
        ''''

1. types.Tool
- JSON中の `tools` 配列の要素に対応。`function_declarations` に関数定義のリストを持たせることで、Geminiに「呼び出せる関数一覧」を伝える器になる。
2. types.FunctionDeclaration
- `functionDeclarations` 配列の各要素に対応。関数の `name`（関数名）・`description`（説明）・`parameters`（引数のJSON Schema）を保持し、Geminiが関数の存在と使い方を理解するための定義。
3. types.GenerateContentConfig
- JSON中の `generationConfig` と `tools` をまとめて保持する設定オブジェクト。`temperature` や `maxOutputTokens` などの生成パラメータに加え、`tools=[TOOLS
]` のようにツール一覧も一緒に渡す。
4. types.FunctionCall
- レスポンス側でGeminiが「この関数をこの引数で呼びたい」と返してきた内容を表す型（`part.function_call`）。`name` と `args` を持ち、ローカル関数を実引数で呼び出すために使う。
5. types.Part
- JSON中の `parts` 配列の要素に対応。テキスト（`text`）や関数呼び出し（`function_call`）、関数の実行結果（`from_function_response` で作る）など、メッセージの中身1つ分を表す最小単位。

# オープンモデルのエコシステム
- オープンモデルのエコシステムはOpenAIのAPIフォーマットがデファクトスタンダードなので、JSON形式はGeminiシリーズと異なり、typesなどは使えない。素朴にJSONを書く

## Streamlitの実行・イベントモデル
Streamlitは伝統的なイベント駆動や無限ループによる待機とは異なる、独自の実行モデルを持っています。

### 1. 「上から下への再実行」モデル
ユーザーがUI操作（ボタンクリック、テキスト入力後のEnterなど）を行うたびに、**Pythonスクリプト全体が1行目から最後まで丸ごと再実行**されます。

### 2. `st.session_state` による状態保持
スクリプトが毎回リセットされるため、通常のローカル変数は実行のたびに消えてしまいます。実行をまたいで状態（チャット履歴やAPIクライアントなど）を保持するには、`st.session_state` という永続的なメモリスペースを利用します。
- **初回ロード時のみの処理**: `if "key" not in st.session_state:` を使って初期化します。

### 3. メッセージ描画とエージェント処理の流れ
1. **履歴の再描画**: `st.session_state.messages` に格納されている過去のチャットログをループで全て描画します。
2. **入力の受付**: `st.chat_input` でユーザーの入力を待ちます。
3. **イベントトリガー**: ユーザーがEnterを押すと、スクリプトが再実行され、`if user_input:` 条件内が実行されます。
   - ユーザーの発言を履歴に追加し描画。
   - エージェント（`run_turn`）を実行して、アシスタントやツールの返答を履歴に追加し、新着メッセージを描画。
4. スクリプトの末尾に到達すると実行が一時停止し、次のユーザー入力を待ちます。


## from .sapleとfrom sampleの違い
* `from sample import ...`（**絶対インポート**）

  * `sys.path`から`sample`を探す（トップレベルのモジュール・パッケージを参照）。

* `from .sample import ...`(**相対インポート**)

  * **現在のパッケージ内**の`sample`を参照する。

例：

```text
mypkg/
├── sample.py
└── utils.py
```

`utils.py`で

```python
from .sample import func
```

と書くと、必ず`mypkg/sample.py`が読み込まれる。

一方、

```python
from sample import func
```

はトップレベルの`sample`を探すため、別の`sample`が見つかる可能性がある。
