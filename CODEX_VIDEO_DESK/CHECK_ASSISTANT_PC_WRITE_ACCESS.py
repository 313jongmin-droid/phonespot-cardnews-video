from __future__ import annotations

import json
import os
import socket
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

TARGETS = [
    ROOT / "CODEX_VIDEO_DESK" / "TEMP",
    ROOT / "CODEX_VIDEO_DESK" / "RESULTS",
    ROOT / "CODEX_VIDEO_DESK" / "ILLUSTRATION_DROP",
    ROOT / "cardnews" / "output",
    ROOT / "shorts" / "public",
    ROOT / "shorts" / "public" / "audio",
    ROOT / "shorts" / "public" / "assets",
]


def check_dir(path: Path) -> tuple[bool, str]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / f"__codex_write_test_{socket.gethostname()}_{os.getpid()}.tmp"
        probe.write_text(datetime.now().isoformat(), encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True, "OK"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - Assistant PC Write Access Check")
    print("============================================================")
    print(f"Root: {ROOT}")
    print("")
    failures = []
    for target in TARGETS:
        ok, msg = check_dir(target)
        mark = "OK " if ok else "NG "
        print(f"[{mark}] {target}")
        if not ok:
            print(f"     {msg}")
            failures.append({"path": str(target), "error": msg})
    print("")
    if failures:
        print("[FAILED] This PC cannot render safely from the shared folder.")
        print("")
        print("Main PC share permissions must allow this assistant PC/user to CHANGE/WRITE:")
        print("- CODEX_VIDEO_DESK")
        print("- cardnews\\output")
        print("- shorts\\public")
        print("- shorts\\public\\audio")
        print("- shorts\\public\\assets")
        print("")
        print("Windows sharing fix on MAIN PC:")
        print("1. Right-click phonespot_cardnews folder > Properties")
        print("2. Sharing > Advanced Sharing > Permissions")
        print("3. Add assistant PC user or Everyone temporarily")
        print("4. Allow Change + Read")
        print("5. Security tab also allow Modify for the same user/group")
        print("")
        report = ROOT / "CODEX_VIDEO_DESK" / "TEMP" / "assistant_write_access_failed.json"
        try:
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Report: {report}")
        except Exception:
            pass
        return 1
    print("[OK] This PC has the write access needed for prompt prep and rendering.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
