import os

from dotenv import load_dotenv
from google import genai
from openai import OpenAI

load_dotenv()

MODEL = "gemma-4-31b-it"
GEMINI_MODEL = "gemini-flash-lite-latest"


def create_client() -> OpenAI:
    """Gemini APIのキーを使って、OpenAI互換クライアントを初期化する。"""
    return OpenAI(
        api_key=os.environ["GEMINI_API_KEY"],
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )


def create_gemini_client() -> genai.Client:
    """素のGemini SDK(google-genai)のクライアントを初期化する。"""
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])
