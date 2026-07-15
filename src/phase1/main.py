# phase1のCLIベースでやり取りするバージョン
import sys
from pathlib import Path

# 親ディレクトリ（src）を検索パスに追加
sys.path.append(str(Path(__file__).parent.parent))

from utils import create_client
from agent import run_turn

def main():
    client = create_client()
    messages = []
    print("Gemma Tool Use デモ（終了するには exit）")

    while True:
        user_input = input("あなた: ")
        if user_input.strip() in ("exit", "quit"):
            break

        messages.append({"role": "user", "content": user_input})
        run_turn(client, messages)

        print(f"Gemma: {messages[-1].content}")


if __name__ == "__main__":
    main()
