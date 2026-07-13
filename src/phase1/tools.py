from datetime import datetime


def get_current_time() -> str:
    """現在の日時を取得する。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ローカル関数名 -> 実体 のマッピング（モデルから関数名で呼ばれたときに引く）
LOCAL_FUNCTIONS = {
    "get_current_time": get_current_time,
}

# OpenAIフォーマットでのツール定義
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "現在の日時を取得する。",
        },
    },
]
