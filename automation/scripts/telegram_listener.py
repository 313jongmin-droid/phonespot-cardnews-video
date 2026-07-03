#!/usr/bin/env python3
"""텔레그램 봇 listener — 사장님 폰에서 `신규 수집` 등 명령 수신.

흐름:
  1. 사장님 폰 텔레그램 -> 봇에 명령 ("신규 수집" / "사기 토픽" / "꿀팁 토픽" / "Q&A 토픽")
  2. 이 listener (PC daemon) 가 long polling으로 수신
  3. 명령을 클립보드에 복사
  4. Claude 데스크탑 앱 자동 실행 (foreground)
  5. mode=manual: 사장님이 Ctrl+V + Enter
     mode=auto:   pyautogui로 자동 키 입력

설정 (_secrets/listener_config.json):
  {
    "mode": "manual",            // 또는 "auto"
    "claude_path": "C:/Users/.../AppData/Local/Programs/Claude/Claude.exe",
    "allowed_commands": {"신규 수집": "신규 수집", ...}
  }
  파일 없으면 기본값 사용. claude_path 없으면 PATH에서 찾음.

실행:
  py automation\\scripts\\telegram_listener.py
  또는: automation\\start_telegram_listener.bat
"""
import sys
import json
import time
import subprocess
import platform
from pathlib import Path
from urllib import request as _urlreq, parse as _urlparse, error as _urlerr

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # automation/scripts -> automation -> root
TOKEN_FILE = PROJECT_ROOT / "_secrets" / "telegram_token.txt"
CHAT_ID_FILE = PROJECT_ROOT / "_secrets" / "telegram_chat_id.txt"
CFG_FILE = PROJECT_ROOT / "_secrets" / "listener_config.json"
OFFSET_FILE = PROJECT_ROOT / "_state" / "telegram_offset.txt"
API_BASE = "https://api.telegram.org/bot{token}"

# 기본 명령 매핑 (config로 override 가능)
DEFAULT_COMMANDS = {
    "신규 수집": "신규 수집",
    "신규 뉴스 수집": "신규 뉴스 수집",
    "사기 토픽": "사기 토픽 수집",
    "꿀팁 토픽": "꿀팁 토픽 수집",
    "Q&A 토픽": "Q&A 토픽 수집",
    "수집": "신규 수집",
    "news": "신규 뉴스 수집",
    "scam": "사기 토픽 수집",
    "tip": "꿀팁 토픽 수집",
    "qa": "Q&A 토픽 수집",
}


# ============================================================
# Helpers
# ============================================================
def load_token() -> str:
    if not TOKEN_FILE.exists():
        sys.exit(f"[error] {TOKEN_FILE} missing")
    t = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not t or ":" not in t:
        sys.exit("[error] bad token format")
    return t


def load_chat_id() -> str:
    if not CHAT_ID_FILE.exists():
        return ""
    return CHAT_ID_FILE.read_text(encoding="utf-8").strip()


def load_config() -> dict:
    cfg = {
        "mode": "manual",
        "claude_path": "",
        "allowed_commands": DEFAULT_COMMANDS,
        "trusted_chat_ids": [],  # 비어있으면 chat_id 1개만 (load_chat_id) 사용
        "broadcast_chat_ids": [],  # ★ outbox 수신 전용 추가 수신자 (명령 권한 없음, 2026-07-03)
    }
    if CFG_FILE.exists():
        try:
            user_cfg = json.loads(CFG_FILE.read_text(encoding="utf-8"))
            cfg.update(user_cfg)
        except Exception as e:
            print(f"[warn] config parse failed: {e}", file=sys.stderr)
    if not cfg["trusted_chat_ids"]:
        chat_id = load_chat_id()
        if chat_id:
            cfg["trusted_chat_ids"] = [chat_id]
    return cfg


def load_offset() -> int:
    if not OFFSET_FILE.exists():
        return 0
    try:
        return int(OFFSET_FILE.read_text(encoding="utf-8").strip() or "0")
    except Exception:
        return 0


def save_offset(offset: int) -> None:
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(str(offset), encoding="utf-8")


def call_api(method: str, params: dict, timeout: int = 35) -> dict:
    token = load_token()
    url = API_BASE.format(token=token) + "/" + method
    data = _urlparse.urlencode(params).encode("utf-8")
    req = _urlreq.Request(url, data=data, method="POST")
    try:
        with _urlreq.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except _urlerr.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"ok": False, "error_code": e.code, "description": body[:400]}
    except _urlerr.URLError as e:
        return {"ok": False, "description": f"network error: {e}"}
    except Exception as e:
        return {"ok": False, "description": f"unexpected: {e}"}


def send_reply(chat_id: str, text: str) -> None:
    r = call_api("sendMessage", {"chat_id": chat_id, "text": text})
    if not r.get("ok"):
        print(f"[warn] reply failed: {r}", file=sys.stderr)


# ============================================================
# Clipboard (Windows stdlib only via powershell)
# ============================================================
def set_clipboard(text: str) -> bool:
    """Windows clipboard set (PowerShell -EncodedCommand 방식 — 인코딩 손실 0)."""
    if platform.system() != "Windows":
        print("[warn] clipboard set requires Windows", file=sys.stderr)
        return False
    try:
        import base64
        # text -> base64 (UTF-16-LE)
        text_b64 = base64.b64encode(text.encode('utf-16-le')).decode('ascii')
        # PowerShell 스크립트
        ps_script = (
            f"$bytes=[Convert]::FromBase64String('{text_b64}');"
            f"$t=[System.Text.Encoding]::Unicode.GetString($bytes);"
            f"Set-Clipboard -Value $t"
        )
        # 스크립트 자체도 UTF-16-LE base64 -> -EncodedCommand로 전달 (인코딩 손실 0)
        script_b64 = base64.b64encode(ps_script.encode('utf-16-le')).decode('ascii')
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-EncodedCommand", script_b64],
            capture_output=True, timeout=10,
        )
        if proc.returncode != 0:
            err = proc.stderr.decode('utf-8', errors='replace')[:200] if proc.stderr else ''
            print(f"[warn] Set-Clipboard rc={proc.returncode} stderr={err}", file=sys.stderr)
        return proc.returncode == 0
    except Exception as e:
        print(f"[warn] clipboard failed: {e}", file=sys.stderr)
        return False


# ============================================================
# Claude app launch
# ============================================================
def launch_claude(cfg: dict) -> bool:
    """UWP AUMID 우선, .exe 경로 차순위, claude:// URL fallback."""
    import os
    aumid = (cfg.get("claude_aumid") or "").strip()
    path = (cfg.get("claude_path") or "").strip()
    # 1순위: AUMID (UWP/MSIX 앱 — Microsoft Store 설치)
    if aumid:
        try:
            subprocess.Popen(["explorer.exe", f"shell:appsfolder\\{aumid}"])
            print(f"[launch] UWP AUMID {aumid} OK", file=sys.stderr)
            return True
        except Exception as e:
            print(f"[warn] AUMID launch failed: {e}", file=sys.stderr)
    # 2순위: .exe 경로 (config에 명시된 경우)
    if path and Path(path).exists():
        try:
            subprocess.Popen([path])
            print(f"[launch] exe {path} OK", file=sys.stderr)
            return True
        except Exception as e:
            print(f"[warn] path launch failed: {e}", file=sys.stderr)
    # 3순위: 자동 탐색 — 일반 설치 경로
    user_home = os.path.expanduser("~")
    fallback_paths = [
        os.path.join(user_home, "AppData", "Local", "Programs", "Claude", "Claude.exe"),
        os.path.join(user_home, "AppData", "Local", "AnthropicClaude", "claude.exe"),
    ]
    for p in fallback_paths:
        if Path(p).exists():
            try:
                subprocess.Popen([p])
                print(f"[launch] fallback {p} OK", file=sys.stderr)
                return True
            except Exception:
                continue
    # 4순위: claude:// URL scheme
    try:
        subprocess.Popen(["cmd", "/c", "start", "", "claude://"], shell=False)
        print("[launch] claude:// URL OK", file=sys.stderr)
        return True
    except Exception:
        return False


def activate_claude_window() -> bool:
    """Claude 앱 창을 foreground로 강제 활성화 (pyautogui 자동 입력 직전 호출)."""
    if platform.system() != "Windows":
        return False
    try:
        ps_script = (
            "$shell = New-Object -ComObject WScript.Shell;"
            "Start-Sleep -Milliseconds 300;"
            "$shell.AppActivate('Claude') | Out-Null"
        )
        import base64
        script_b64 = base64.b64encode(ps_script.encode('utf-16-le')).decode('ascii')
        subprocess.run(
            ["powershell", "-NoProfile", "-EncodedCommand", script_b64],
            capture_output=True, timeout=5,
        )
        return True
    except Exception as e:
        print(f"[warn] activate_claude_window failed: {e}", file=sys.stderr)
        return False


def auto_type(text: str, delay_sec: float = 2.0) -> bool:
    """pyautogui 자동 키 입력 (mode=auto 일 때만). Claude 창 강제 활성화 포함."""
    try:
        import pyautogui  # noqa
    except ImportError:
        print("[warn] pyautogui not installed (pip install pyautogui)", file=sys.stderr)
        return False
    try:
        import pyautogui
        # 1. Claude 창 강제 활성화
        activate_claude_window()
        time.sleep(delay_sec)  # 앱 활성화 + foreground 대기
        # 2. 클립보드에 이미 박혀있으므로 Ctrl+V + Enter
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.3)
        pyautogui.press('enter')
        return True
    except Exception as e:
        print(f"[warn] auto_type failed: {e}", file=sys.stderr)
        return False


# ============================================================
# Command handling
# ============================================================
def handle_command(chat_id: str, text: str, cfg: dict) -> None:
    text = text.strip()
    cmds = cfg.get("allowed_commands", DEFAULT_COMMANDS)
    # 정확 매칭 우선, 없으면 부분 매칭
    final_cmd = cmds.get(text)
    if not final_cmd:
        for k, v in cmds.items():
            if k.lower() == text.lower() or k in text:
                final_cmd = v
                break
    if not final_cmd:
        send_reply(chat_id, (
            f"명령어를 인식하지 못했습니다: '{text}'\n"
            f"사용 가능: {', '.join(cmds.keys())}"
        ))
        return

    send_reply(chat_id, f"명령 수신: {final_cmd}\nPC에서 Claude 앱 열고 처리 시작합니다.")

    # 1. 클립보드에 명령어 박기
    clip_ok = set_clipboard(final_cmd)
    # 2. Claude 앱 실행
    launch_ok = launch_claude(cfg)
    # 3. mode=auto면 자동 입력
    mode = cfg.get("mode", "manual")
    typed = False
    if mode == "auto":
        typed = auto_type(final_cmd)

    # 결과 회신
    parts = []
    parts.append(f"클립보드: {'OK' if clip_ok else 'FAIL'}")
    parts.append(f"Claude 앱 실행: {'OK' if launch_ok else 'FAIL'}")
    if mode == "auto":
        parts.append(f"자동 입력: {'OK' if typed else 'FAIL (Ctrl+V + Enter 직접)'}")
    else:
        parts.append("manual 모드: PC에서 Ctrl+V + Enter 눌러주세요")
    send_reply(chat_id, " / ".join(parts))


# ============================================================
# Outbox watcher — _state/outbox/*.txt → 자동 푸시 → outbox_sent/
# ============================================================
OUTBOX_DIR = PROJECT_ROOT / "_state" / "outbox"
OUTBOX_SENT_DIR = PROJECT_ROOT / "_state" / "outbox_sent"

def check_outbox(recipients: list) -> None:
    # recipients = trusted 대표 1명 + broadcast_chat_ids (★ 2026-07-03 다중 수신)
    if not OUTBOX_DIR.exists():
        return
    targets = sorted(OUTBOX_DIR.glob("*.txt"))
    if not targets:
        return
    OUTBOX_SENT_DIR.mkdir(parents=True, exist_ok=True)
    if not recipients:
        return
    for f in targets:
        try:
            text = f.read_text(encoding="utf-8")
            # 텔레그램 4096자 제한 — 초과 시 분할
            chunks = [text[i:i+3800] for i in range(0, len(text), 3800)] or [""]
            ok_all = True
            for cid in recipients:
                for i, ch in enumerate(chunks):
                    prefix = f"[{i+1}/{len(chunks)}]\n" if len(chunks) > 1 else ""
                    r = call_api("sendMessage", {
                        "chat_id": cid,
                        "text": prefix + ch,
                        "disable_web_page_preview": "true",
                    })
                    # 응답 body 전체 로깅 (진단용)
                    print(f"[outbox] chat_id={cid} resp_ok={r.get('ok')} message_id={r.get('result',{}).get('message_id')} desc={r.get('description','')[:200]}")
                    if not r.get("ok"):
                        ok_all = False
                        print(f"[outbox] send failed full: {r}", file=sys.stderr)
                        break
                if not ok_all:
                    break  # 일부 실패 시 파일 잔존 → 다음 사이클 재시도 (성공 수신자는 중복 수신 가능)
            if ok_all:
                dst = OUTBOX_SENT_DIR / f.name
                if dst.exists():
                    dst.unlink()
                f.rename(dst)
                print(f"[outbox] sent + moved: {f.name}")
        except Exception as e:
            print(f"[outbox] error on {f.name}: {e}", file=sys.stderr)


# ============================================================
# Main loop
# ============================================================
def poll_loop() -> None:
    cfg = load_config()
    trusted = set(cfg.get("trusted_chat_ids", []))
    if not trusted:
        sys.exit("[error] no trusted chat_id. run telegram_notify.py --setup first")
    # outbox 수신자 = trusted 첫 번째(사장님) + broadcast 추가 수신자 (명령 권한은 trusted만)
    outbox_recipients = list(cfg.get("trusted_chat_ids", []))[:1] + [str(c) for c in cfg.get("broadcast_chat_ids", []) if c]
    offset = load_offset()
    print(f"[listener] start. trusted_chat_ids={trusted} mode={cfg.get('mode')}")
    print(f"[listener] commands: {list(cfg.get('allowed_commands', DEFAULT_COMMANDS).keys())}")
    while True:
        try:
            r = call_api("getUpdates", {"offset": offset, "timeout": 30}, timeout=35)
        except KeyboardInterrupt:
            print("[listener] stopped by user")
            break
        if not r.get("ok"):
            print(f"[warn] getUpdates failed: {r.get('description', r)}", file=sys.stderr)
            time.sleep(5)
            continue
        for upd in r.get("result", []):
            offset = max(offset, upd.get("update_id", 0) + 1)
            msg = upd.get("message") or upd.get("edited_message") or {}
            chat = msg.get("chat", {})
            chat_id = str(chat.get("id", ""))
            text = msg.get("text", "")
            if not chat_id or not text:
                continue
            if trusted and chat_id not in trusted:
                print(f"[listener] ignored untrusted chat_id={chat_id}")
                continue
            print(f"[listener] msg from {chat_id}: {text!r}")
            try:
                handle_command(chat_id, text, cfg)
            except Exception as e:
                print(f"[error] handle_command failed: {e}", file=sys.stderr)
                send_reply(chat_id, f"err: {e}")
        save_offset(offset)
        # outbox 자동 푸시 (클로드가 _state/outbox/*.txt 떨구면 자동 전송)
        try:
            check_outbox(outbox_recipients)
        except Exception as e:
            print(f"[warn] outbox check failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    try:
        poll_loop()
    except KeyboardInterrupt:
        print("\n[listener] exit")
