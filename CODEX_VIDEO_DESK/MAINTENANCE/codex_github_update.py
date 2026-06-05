from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SHORTS = ROOT / "shorts"
TEMP = ROOT / "CODEX_VIDEO_DESK" / "TEMP"
LOCAL_LOG_DIR = Path(tempfile.gettempdir()) / "PhoneSpotCodexVideo"
LOG_PATH = TEMP / "github_update.log"


RUNTIME_PREFIXES = (
    "CODEX_VIDEO_DESK/RESULTS/",
    "CODEX_VIDEO_DESK/WORK_QUEUE/",
    "CODEX_VIDEO_DESK/TEMP/",
    "CODEX_VIDEO_DESK/ILLUSTRATION_DROP/",
    "CODEX_VIDEO_DESK/GOOGLE_SHEETS_PANEL/",
    "shorts/out_codex/",
    "shorts/public/audio/",
    "shorts/public/assets/",
    "cardnews/output/",
    "cardnews/images/",
)

RUNTIME_SUFFIXES = (
    ".log",
    ".tmp",
    ".bak",
    ".mp4",
    ".mp3",
)


def safe_log_path() -> Path:
    try:
        TEMP.mkdir(parents=True, exist_ok=True)
        probe = TEMP / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return TEMP / "github_update.log"
    except OSError:
        LOCAL_LOG_DIR.mkdir(parents=True, exist_ok=True)
        return LOCAL_LOG_DIR / "github_update.log"


def is_network_root() -> bool:
    return str(ROOT).startswith("\\\\")


def log(message: str = "") -> None:
    print(message)
    path = safe_log_path()
    with path.open("a", encoding="utf-8", errors="replace") as fh:
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
    log("")
    log("[cmd] " + " ".join(command))
    result = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.stdout:
        for line in result.stdout.splitlines():
            log(line)
    if check and result.returncode:
        raise SystemExit(result.returncode)
    return result


def status_lines() -> list[str]:
    result = subprocess.run(
        [GIT, "status", "--short"],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def is_runtime_status_line(line: str) -> bool:
    # porcelain short status: XY path
    path = line[3:].replace("\\", "/").strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[-1].strip()
    if any(path.startswith(prefix) for prefix in RUNTIME_PREFIXES):
        return True
    if any(path.endswith(suffix) for suffix in RUNTIME_SUFFIXES):
        return True
    # Untracked markdown/json files in Codex desk are generated notes/state.
    if line.startswith("?? ") and path.startswith("CODEX_VIDEO_DESK/"):
        return True
    return False


def main() -> int:
    log_path = safe_log_path()
    try:
        if log_path.exists():
            log_path.unlink()
    except OSError:
        pass

    log("============================================================")
    log(" PhoneSpot Codex - GitHub System Update")
    log("============================================================")
    log(f"Root: {ROOT}")
    if is_network_root():
        log("[NETWORK MODE] This updater is running from a shared network folder.")
        log("[HINT] Render/helper PCs should run their local clone, e.g. C:\\PhoneSpot\\phonespot_cardnews, not \\\\main-pc\\phonespot_cardnews.")
        log("[HINT] Run 00_SETUP_RENDER_PC_FROM_GITHUB.bat on the helper PC, then open its local CODEX_VIDEO_DESK panel.")
        return 4

    if not (ROOT / ".git").exists():
        log("[ERROR] This folder is not a Git repository yet.")
        return 2
    if not GIT:
        log("[ERROR] Git was not found. Install Git for Windows or GitHub Desktop.")
        return 2
    log(f"[git] {GIT}")

    run([GIT, "--version"])
    run([GIT, "remote", "-v"], check=False)

    lines = status_lines()
    blocking = [line for line in lines if not is_runtime_status_line(line)]
    ignored = [line for line in lines if is_runtime_status_line(line)]

    if ignored:
        log("")
        log(f"[INFO] Ignoring runtime/generated local changes: {len(ignored)}")
        for line in ignored[:30]:
            log("  " + line)

    if blocking:
        log("")
        log("[STOP] Code/config local changes exist. Commit, discard, or push them before update.")
        for line in blocking[:80]:
            log("  " + line)
        log("")
        log("[HINT] This protects the system from overwriting active development changes.")
        return 3

    run([GIT, "pull", "--ff-only"])

    if (SHORTS / "package.json").exists():
        log("")
        log("[deps] npm install")
        run(["cmd", "/c", "npm install"], cwd=SHORTS)

    log("")
    log("[deps] Python packages")
    pip = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "edge-tts", "mutagen", "pillow", "requests"],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if pip.stdout:
        for line in pip.stdout.splitlines():
            log(line)

    refresh = ROOT / "shorts" / "scripts" / "codex_refresh_workbench.py"
    if refresh.exists():
        result = subprocess.run(
            [sys.executable, str(refresh)],
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if result.stdout:
            for line in result.stdout.splitlines():
                log(line)

    status_script = ROOT / "CODEX_VIDEO_DESK" / "MAINTENANCE" / "codex_github_status.py"
    if status_script.exists():
        subprocess.run([sys.executable, str(status_script)], cwd=str(ROOT))

    log("")
    log("[OK] System update complete. Restart the panel if it was already open.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
