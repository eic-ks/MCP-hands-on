import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = "gemma-4-31b-it"


def create_client() -> OpenAI:
    """Gemini APIのキーを使って、OpenAI互換クライアントを初期化する。"""
    return OpenAI(
        api_key=os.environ["GEMINI_API_KEY"],
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
