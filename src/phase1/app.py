import streamlit as st

from agent import run_turn
from llm_client import create_client


def get_role(message) -> str:
    return message["role"] if isinstance(message, dict) else message.role


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
        st.markdown(content)


st.set_page_config(page_title="Gemma Tool Use デモ")
st.title("Gemma Tool Use デモ")

if "client" not in st.session_state:
    st.session_state.client = create_client()
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    render_message(message)

user_input = st.chat_input("あなたのメッセージ")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    new_message_start = len(st.session_state.messages)
    with st.spinner("考え中..."):
        run_turn(st.session_state.client, st.session_state.messages)

    for message in st.session_state.messages[new_message_start:]:
        render_message(message)
