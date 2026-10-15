"""Chat thử trên terminal với pipeline thật (không cần chạy API).

    python scripts/chat_cli.py            # gõ /reset để mở phiên mới, /quit để thoát
"""
import os
import sys
import uuid

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.pipeline import build_default_pipeline  # noqa: E402


def main():
    p = build_default_pipeline()
    sid = uuid.uuid4().hex
    print("Chatbot sẵn sàng. /reset = phiên mới, /quit = thoát.\n")
    while True:
        try:
            msg = input("Bạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not msg:
            continue
        if msg == "/quit":
            break
        if msg == "/reset":
            sid = uuid.uuid4().hex
            print("-- phiên mới --\n")
            continue
        r = p.handle(sid, msg)
        print(f"\nBot: {r['reply']}")
        print(f"     [nhánh {r['branch']} | states {r['states']} | thuốc {r['medication']} | {r['latency_s']}s]\n")


if __name__ == "__main__":
    main()
