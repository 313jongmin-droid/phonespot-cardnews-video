from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SHORTS = ROOT / "shorts"
DESK = ROOT / "CODEX_VIDEO_DESK"


def run(command: list[str], cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess:
    print("")
    print("[cmd] " + " ".join(command))
    result = subprocess.run(command, cwd=str(cwd), text=True)
    if check and result.returncode:
        raise SystemExit(result.returncode)
    return result


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - GitHub System Update")
    print("============================================================")
    print(f"Root: {ROOT}")
    print("")

    if not (ROOT / ".git").exists():
        print("[ERROR] This folder is not a Git repository yet.")
        print("")
        print("Use GitHub only after the project is cloned locally, for example:")
        print(r"  C:\PhoneSpot\phonespot_cardnews")
        print("")
        print("Initial setup should clone from GitHub first. This updater only runs git pull.")
        return 2

    run(["git", "--version"])
    run(["git", "remote", "-v"], check=False)

    print("")
    print("[check] local changes")
    status = subprocess.run(["git", "status", "--short"], cwd=str(ROOT), text=True, capture_output=True)
    dirty_lines = [line for line in status.stdout.splitlines() if line.strip()]
    if dirty_lines:
        print("[WARN] Local changes exist. Runtime folders should be ignored by .gitignore.")
        for line in dirty_lines[:40]:
            print("  " + line)
        if len(dirty_lines) > 40:
            print(f"  ... {len(dirty_lines) - 40} more")
        print("")
        print("[STOP] Commit/stash intentionally before pulling to avoid overwriting work.")
        return 3

    run(["git", "pull", "--ff-only"])

    if (SHORTS / "package.json").exists():
        print("")
        print("[deps] npm install")
        run(["cmd", "/c", "npm install"], cwd=SHORTS)

    print("")
    print("[deps] Python packages")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "edge-tts", "mutagen"], cwd=str(ROOT))

    refresh = ROOT / "shorts" / "scripts" / "codex_refresh_workbench.py"
    if refresh.exists():
        subprocess.run([sys.executable, str(refresh)], cwd=str(ROOT))

    print("")
    print("[OK] System update complete. Restart the panel if it was already open.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
