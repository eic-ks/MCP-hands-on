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

この構成を理解するために、3つのフェーズに分けて開発する。

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