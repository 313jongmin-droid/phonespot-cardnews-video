# -*- coding: utf-8 -*-
from __future__ import annotations

import secrets
import string
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SECRETS = ROOT / "_secrets"
DESK = ROOT / "CODEX_VIDEO_DESK"
AUTH = SECRETS / "panel_auth.txt"
WORKER_KEY = SECRETS / "worker_api_key.txt"
INFO = DESK / "TEMP" / "PANEL_ACCESS_INFO.txt"


def token(length: int = 18) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main() -> int:
    SECRETS.mkdir(parents=True, exist_ok=True)
    INFO.parent.mkdir(parents=True, exist_ok=True)
    created = False
    if not AUTH.exists():
        AUTH.write_text(f"phonespot:{token(14)}\n", encoding="utf-8")
        created = True
    if not WORKER_KEY.exists():
        WORKER_KEY.write_text(token(32) + "\n", encoding="utf-8")
        created = True
    username, password = AUTH.read_text(encoding="utf-8-sig").strip().split(":", 1)
    worker_key = WORKER_KEY.read_text(encoding="utf-8-sig").strip()
    INFO.write_text(
        "PhoneSpot Panel Access\n"
        "======================\n\n"
        f"Username: {username}\n"
        f"Password: {password}\n\n"
        "Render PC setup key:\n"
        f"{worker_key}\n\n"
        "Keep this file private.\n",
        encoding="utf-8",
    )
    print(f"[security] access info: {INFO}")
    print("[security] created" if created else "[security] ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
