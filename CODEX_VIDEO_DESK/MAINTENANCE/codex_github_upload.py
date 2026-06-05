from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMP = ROOT / "CODEX_VIDEO_DESK" / "TEMP"
LOG_PATH = TEMP / "github_upload.log"


def log(message: str = "") -> None:
    print(message)
    TEMP.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8", errors="replace") as fh:
        fh.write(message + "\n")


def find_git() -> str | None:
    candidates = [
        "git",
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
    ]
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    if local:
        candidates.extend(
            str(p)
            for p in sorted((local / "GitHubDesktop").glob(r"app-*\resources\app\git\cmd\git.exe"), reverse=True)
        )
    for candidate in candidates:
        try:
            result = subprocess.run([candidate, "--version"], cwd=str(ROOT), text=True, encoding="utf-8", errors="replace", capture_output=True)
            if result.returncode == 0:
                return candidate
        except FileNotFoundError:
            continue
    return None


GIT = find_git()


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess:
    log("")
    log("[cmd] " + " ".join(command))
    result = subprocess.run(command, cwd=str(ROOT), text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.stdout:
        for line in result.stdout.splitlines():
            log(line)
    if check and result.returncode:
        raise SystemExit(result.returncode)
    return result


def main() -> int:
    if LOG_PATH.exists():
        LOG_PATH.unlink()
    log("============================================================")
    log(" PhoneSpot Codex - GitHub Upload")
    log("============================================================")
    log(f"Root: {ROOT}")

    if not (ROOT / ".git").exists():
        log("[ERROR] This folder is not a Git repository yet.")
        return 2
    if not GIT:
        log("[ERROR] Git was not found. Install Git for Windows or GitHub Desktop.")
        return 2

    run([GIT, "--version"])
    run([GIT, "status", "--short"], check=False)
    run([GIT, "add", "-A"])

    diff = run([GIT, "diff", "--cached", "--name-only"], check=False)
    changed = [line.strip() for line in (diff.stdout or "").splitlines() if line.strip()]
    if not changed:
        log("[OK] No changes to upload.")
        return 0

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    message = f"Update PhoneSpot Codex system {stamp}"
    log("")
    log(f"[commit] {message}")
    run([GIT, "commit", "-m", message])
    run([GIT, "push"])

    status_script = ROOT / "CODEX_VIDEO_DESK" / "MAINTENANCE" / "codex_github_status.py"
    if status_script.exists():
        subprocess.run([sys.executable, str(status_script)], cwd=str(ROOT))

    log("")
    log("[OK] Upload complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
