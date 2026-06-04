"""
텔레그램 전송 공용 헬퍼.
- send_text(msg) 함수 호출만으로 _secrets/ 의 token + chat_id 로드 후 푸시.
- CLI 사용: py -3 tg_send.py <txt_path>  → 파일 내용을 1회 전송.
"""
import sys
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SECRETS = ROOT / "_secrets"

def _load(name: str) -> str:
    return (SECRETS / name).read_text(encoding="utf-8").strip()

def send_text(text: str, chat_id: str | None = None) -> tuple[bool, str]:
    token = _load("telegram_token.txt")
    cid = chat_id or _load("telegram_chat_id.txt")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": cid,
        "text": text,
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return (200 <= resp.status < 300), body
    except Exception as e:
        return False, f"ERROR: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: py -3 tg_send.py <txt_path>")
        sys.exit(2)
    p = Path(sys.argv[1])
    ok, body = send_text(p.read_text(encoding="utf-8"))
    print(f"ok={ok}\n{body[:300]}")
    sys.exit(0 if ok else 1)
