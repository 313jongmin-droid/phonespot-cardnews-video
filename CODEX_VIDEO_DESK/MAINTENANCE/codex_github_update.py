from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SHORTS = ROOT / "shorts"


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
            for p in sorted(
                (local / "GitHubDesktop").glob(r"app-*\resources\app\git\cmd\git.exe"),
                reverse=True,
            )
        )
    for candidate in candidates:
        try:
            result = subprocess.run(
                [candidate, "--version"],
                cwd=str(ROOT),
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            )
            if result.returncode == 0:
                return candidate
        except FileNotFoundError:
            continue
    return None


GIT = find_git()


def run(command: list[str], cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess:
    print("")
    print("[cmd] " + " ".join(command))
    result = subprocess.run(command, cwd=str(cwd), text=True, encoding="utf-8", errors="replace")
    if check and result.returncode:
        raise SystemExit(result.returncode)
    return result


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - GitHub System Update")
    print("============================================================")
    print(f"Root: {ROOT}")

    if not (ROOT / ".git").exists():
        print("[ERROR] This folder is not a Git repository yet.")
        return 2
    if not GIT:
        print("[ERROR] Git was not found. Install Git for Windows or GitHub Desktop.")
        return 2
    print(f"[git] {GIT}")

    run([GIT, "--version"])
    run([GIT, "remote", "-v"], check=False)

    status = subprocess.run(
        [GIT, "status", "--short"],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    dirty_lines = [line for line in status.stdout.splitlines() if line.strip()]
    if dirty_lines:
        print("[STOP] Local changes exist. Commit, discard, or back them up before update.")
        for line in dirty_lines[:60]:
            print("  " + line)
        return 3

    run([GIT, "pull", "--ff-only"])

    if (SHORTS / "package.json").exists():
        print("")
        print("[deps] npm install")
        run(["cmd", "/c", "npm install"], cwd=SHORTS)

    print("")
    print("[deps] Python packages")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "edge-tts", "mutagen", "pillow", "requests"], cwd=str(ROOT))

    refresh = ROOT / "shorts" / "scripts" / "codex_refresh_workbench.py"
    if refresh.exists():
        subprocess.run([sys.executable, str(refresh)], cwd=str(ROOT))

    print("")
    print("[OK] System update complete. Restart the panel if it was already open.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
