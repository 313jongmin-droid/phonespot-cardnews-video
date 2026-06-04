#!/usr/bin/env python3
"""텔레그램 봇 알림 helper.

용도: 미니 PC daemon이 야간 자동화 진행 상황을 사장님 폰으로 푸시.
표준 라이브러리만 사용 (requests 불필요).

설정:
  1. telegram_token.txt — BotFather 발급 토큰 (.gitignore 보호)
  2. telegram_chat_id.txt — 사장님 chat_id (자동 추출됨)

사용:
  # 셋업 (1회): 사장님이 봇에 메시지 1번 보낸 후
  py scripts\\telegram_notify.py --setup
  → chat_id 자동 추출·저장

  # 테스트
  py scripts\\telegram_notify.py --test
  → "Hello from phonespot daemon" 전송

  # 스크립트에서 호출
  from telegram_notify import send
  send("뉴스 수집 완료")
"""
import sys
import json
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # automation/scripts/ -> automation/ -> root
TOKEN_FILE = PROJECT_ROOT / "_secrets" / "telegram_token.txt"
CHAT_ID_FILE = PROJECT_ROOT / "_secrets" / "telegram_chat_id.txt"
API_BASE = "https://api.telegram.org/bot{token}"


def load_token() -> str:
    if not TOKEN_FILE.exists():
        sys.exit(f"[error] {TOKEN_FILE} 없음. BotFather 토큰 저장 필요.")
    t = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not t or ":" not in t:
        sys.exit(f"[error] 토큰 형식 비정상. 예: 1234567890:ABC...")
    return t


def load_chat_id() -> str:
    if not CHAT_ID_FILE.exists():
        return ""
    return CHAT_ID_FILE.read_text(encoding="utf-8").strip()


def call_api(method: str, params: dict, timeout: int = 15) -> dict:
    token = load_token()
    url = API_BASE.format(token=token) + "/" + method
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"ok": False, "error_code": e.code, "description": body[:400]}
    except urllib.error.URLError as e:
        return {"ok": False, "description": f"network error: {e}"}


def setup() -> None:
    """봇과 첫 대화 후 1회 실행 — chat_id 자동 추출."""
    print("[setup] getUpdates 호출 중...")
    r = call_api("getUpdates", {})
    if not r.get("ok"):
        sys.exit(f"[error] API 호출 실패: {r}")
    updates = r.get("result", [])
    if not updates:
        sys.exit(
            "[error] 메시지 없음.\n"
            "  먼저 텔레그램에서 봇(@PLauto_claude_bot)을 검색해\n"
            "  '/start' 또는 아무 메시지 1번 보낸 후 다시 실행하세요."
        )
    # 가장 최근 메시지의 chat_id
    chat_id = str(updates[-1].get("message", {}).get("chat", {}).get("id", ""))
    if not chat_id:
        sys.exit(f"[error] chat_id 추출 실패. 응답: {updates[-1]}")
    CHAT_ID_FILE.write_text(chat_id, encoding="utf-8")
    print(f"[setup] chat_id 저장: {chat_id} -> {CHAT_ID_FILE}")
    # 테스트 메시지
    send("✅ 텔레그램 봇 셋업 완료. 이 메시지가 보이면 정상입니다.")
    print("[setup] 테스트 메시지 발송 완료.")


def send(message: str) -> bool:
    """알림 전송. True/False 반환."""
    chat_id = load_chat_id()
    if not chat_id:
        print("[warn] chat_id 없음. --setup 먼저 실행하세요.", file=sys.stderr)
        return False
    r = call_api("sendMessage", {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    })
    if not r.get("ok"):
        print(f"[error] 전송 실패: {r}", file=sys.stderr)
        return False
    return True


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "--setup":
        setup()
    elif cmd == "--test":
        msg = sys.argv[2] if len(sys.argv) > 2 else "Hello from phonespot daemon"
        ok = send(msg)
        sys.exit(0 if ok else 1)
    else:
        print(f"unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
