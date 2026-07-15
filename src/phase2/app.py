import streamlit as st

import atexit
import sys
import re
from pathlib import Path


# 親ディレクトリ（src）を検索パスに追加
sys.path.append(str(Path(__file__).parent.parent))

from utils import create_client
from client import McpSession


def get_role(message) -> str:
    return message["role"] if isinstance(message, dict) else message.role

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


def render_message(message) -> None:
    role = get_role(message)

    if role == "tool":
        with st.chat_message("assistant"):
            st.caption(f"🔧 {message['name']} を実行")
            st.code(message["content"], language=None)
        return

    content = message["content"] if isinstance(message, dict) else message.content
    if not content:
        return
    with st.chat_message(role):
        formatted = format_content(content, raw=False)
        st.text(formatted)

        if formatted != content:
            with st.expander("生のLLM出力"):
                st.text(content)


st.set_page_config(page_title="Gemma Tool Use デモ")
st.title("Gemma Tool Use デモ")


if "client" not in st.session_state:
    st.session_state.client = create_client()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "mcp" not in st.session_state:
    # MCPセッション(子プロセス+ハンドシェイク)を初回だけ確立し、以後のrerunで使い回す
    st.session_state.mcp = McpSession()
    # プロセス終了時にサーバー子プロセスも含めてクローズする
    atexit.register(st.session_state.mcp.close)

for message in st.session_state.messages:
    render_message(message)

user_input = st.chat_input("あなたのメッセージ")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    new_message_start = len(st.session_state.messages)
    with st.spinner("考え中..."):
        st.session_state.mcp.run_turn(st.session_state.client, st.session_state.messages)

    for message in st.session_state.messages[new_message_start:]:
        render_message(message)
