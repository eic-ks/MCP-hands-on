from datetime import datetime


def get_current_time() -> str:
    """現在の日時を取得する。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
