import streamlit as st

import atexit
import re
import sys
from pathlib import Path


# 親ディレクトリ（src）を検索パスに追加
sys.path.append(str(Path(__file__).parent.parent))

from google.genai import types

from utils import create_gemini_client
from client import McpSession


def format_content(content: str, raw: bool) -> str:
    if raw:
        return content

    # 必要に応じてフィルタを追加
    content = re.sub(
        r"<thought>.*?</thought>",
        "",
        content,
        flags=re.DOTALL,
    )

    return content.strip()


def render_content(content: types.Content) -> None:
    """types.Content内のpartsを、種類（テキスト/ツール呼び出し/ツール結果）ごとに描画する。"""
    for part in content.parts or []:
        if part.function_call is not None:
            with st.chat_message("assistant"):
                st.caption(f"🔧 {part.function_call.name} を実行")
                st.code(str(part.function_call.args), language=None)

        elif part.function_response is not None:
            with st.chat_message("assistant"):
                st.caption(f"🔧 {part.function_response.name} の結果")
                st.code(str(part.function_response.response), language=None)

        elif part.text:
            role = "user" if content.role == "user" else "assistant"
            with st.chat_message(role):
                formatted = format_content(part.text, raw=False)
                st.text(formatted)

                if formatted != part.text:
                    with st.expander("生のLLM出力"):
                        st.text(part.text)


st.set_page_config(page_title="Gemini Tool Use デモ")
st.title("Gemini Tool Use デモ（素のSDK + MCP）")


if "client" not in st.session_state:
    st.session_state.client = create_gemini_client()
if "contents" not in st.session_state:
    st.session_state.contents: list[types.Content] = []
if "mcp" not in st.session_state:
    # MCPセッション(子プロセス+ハンドシェイク)を初回だけ確立し、以後のrerunで使い回す
    st.session_state.mcp = McpSession()
    # プロセス終了時にサーバー子プロセスも含めてクローズする
    atexit.register(st.session_state.mcp.close)

for content in st.session_state.contents:
    render_content(content)

user_input = st.chat_input("あなたのメッセージ")
if user_input:
    st.session_state.contents.append(types.Content(role="user", parts=[types.Part(text=user_input)]))
    with st.chat_message("user"):
        st.markdown(user_input)

    new_content_start = len(st.session_state.contents)
    with st.spinner("考え中..."):
        st.session_state.mcp.run_turn(st.session_state.client, st.session_state.contents)

    for content in st.session_state.contents[new_content_start:]:
        render_content(content)
