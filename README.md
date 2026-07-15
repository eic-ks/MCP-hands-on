# MCP-hands-on

# ハンズオン：Tool UseからMCPサーバーまで

## ゴール

最終的に以下の構成を作る。

```
Gemini API
        │
        ▼
Gemini SDK
        │
        ▼
MCP Client
        │
        ▼
自作MCP Server
        │
        ▼
Local Tool
```

この構成を理解するために、5つのフェーズに分けて開発する。

---

# Phase 1：通常のTool Useを理解する

## 目的

Function Callingの仕組みを理解する。

MCPを使わず、

```
Gemini
    ↓
Function Call
    ↓
Python関数
```

を実装する。

## 作るもの

例として

```
現在時刻を返すTool
```

を実装する。

Tool

```
get_current_time()
```

ユーザー

```
今何時？
```

↓

Gemini

```
Toolを呼ぶ
```

↓

Python

```
現在時刻取得
```

↓

Gemini

```
現在時刻は〜です
```

## 学ぶこと

- Tool Schema
- Function Calling
- Tool Result
- 会話ループ

---

# Phase 2：ToolをMCPサーバー化する

## 目的

Phase1のToolをそのままMCPへ公開する。

```
get_current_time()

↓

@mcp.tool()
```

に変更する。

構成

```
Local Tool

↓

MCP Server

↓

Gemini（まだSDK接続しない）
```

## 学ぶこと

- FastMCP
- Tool登録
- Tool Discovery
- MCP Server起動

---

# Phase 3：SDKからMCPサーバーを利用する

## 目的

Gemini SDKへ

```
このMCPサーバーを使って
```

と設定する。

すると

```
Gemini

↓

SDK

↓

MCP Client

↓

MCP Server

↓

Tool
```

となる。

ToolはSDKへ登録しない。

SDKは

MCPサーバーからTool一覧を取得する。

## 学ぶこと

- MCP Client
- SDK設定
- Tool Discovery
- Tool実行

---

# Phase 4：Tool複数化・Discoveryの本格活用

## 目的

MCPサーバーが公開するToolを1つから複数に増やし、

```
Tool Discovery
```

が複数ツールでも正しく機能することを確認する。

## 作るもの

`get_current_time`に加えて、例えば

```
電卓（四則演算）
天気取得
```

のようなToolをMCPサーバーに追加する。

```
Local Tool（複数）

↓

@mcp.tool()（複数登録）

↓

tools/list（複数件返る）

↓

SDK（複数件から適切なToolを選んで呼ぶ）
```

## 学ぶこと

- 複数Toolの登録
- Tool Discoveryのスケール（1件前提のコードに隠れた決め打ちがないかの確認）
- モデルが複数Toolから適切な1つを選ぶ挙動

---

# Phase 5：他のMCP用途（Resources/Prompts）

## 目的

MCPはTool（関数実行）だけのプロトコルではない。

```
Resources（データ提供）
Prompts（プロンプトテンプレート）
```

というTool以外の機能も学び、MCPサーバー側に追加する。

## 作るもの

```
Resources
```

```
ファイルやドキュメントなど、実行を伴わない「データ」をMCP経由で公開する
```

```
Prompts
```

```
よく使う指示文をテンプレート化し、MCPサーバー側から提供する
```

## 学ぶこと

- Resources（`@mcp.resource()`）
- Prompts（`@mcp.prompt()`）
- Toolとの違い（「実行」ではなく「データ／テンプレートの提供」）
- SDK側でResources/Promptsをどう取得・利用するか

---

# 最終成果物

```
project/

├── server.py
├── tools.py
├── client.py
├── pyproject.toml
└── README.md
```

server.py

```
MCPサーバー
```

tools.py

```
ローカルTool
```

client.py

```
Gemini SDK
```

---

# なぜこの順番なのか

もし最初からMCPを触ると

```
MCPだから動いている
```

という理解になってしまう。

しかし実際には

```
Tool

↓

Function Calling

↓

MCP

↓

SDK
```

という積み重ねになっている。

そのため

1. Tool Use
2. MCP化
3. SDK統合

の順番で進めると

「MCPはFunction Callingを標準化したインターフェースである」

ことが自然に理解できる。