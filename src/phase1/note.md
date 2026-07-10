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