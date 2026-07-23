# 使用方法

## 事前準備
### 1. 環境変数の設定
- Google AI StudioでGeminiAPIKeyを発行する
- .envファイルに設定する

```bash
uv sync
```

```bash
cd MCP-hands-on
```
```bash
# Web UIの場合
uv run streamlit run src/phase2/app.py 

# CLIのインタラクションの場合
uv run src/phase2/main.py 
```