from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMP = ROOT / "CODEX_VIDEO_DESK" / "TEMP"
LOG_PATH = TEMP / "github_upload.log"


def clear_stale_lock() -> None:
    """index.lock 잔재 정리 (2026-06-22). 60초 이상 묵은 락=crash 잔재로 보고 제거.
    활성 작업(<60초)은 건드리지 않아 동시 실행과 충돌 안 함. 이게 '커밋이 락에 막힘' 근본 차단."""
    lock = ROOT / ".git" / "index.lock"
    if not lock.exists():
        return
    try:
        age = time.time() - lock.stat().st_mtime
    except OSError:
        age = 9999
    if age > 60:
        try:
            lock.unlink()
            log(f"[lock] stale index.lock removed (age {int(age)}s)")
        except OSError as e:
            log(f"[lock] remove failed: {e}")
    else:
        log(f"[lock] active index.lock (age {int(age)}s) - skip")


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


def ahead_count() -> int:
    result = subprocess.run(
        [GIT, "rev-list", "--count", "@{u}..HEAD"],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        return int((result.stdout or "0").strip())
    except ValueError:
        return 0


def push_with_retry() -> int:
    attempts = 2
    last_code = 0
    for attempt in range(1, attempts + 1):
        log("")
        log(f"[push] attempt {attempt}/{attempts}")
        result = run([GIT, "push"], check=False)
        last_code = result.returncode
        if result.returncode == 0:
            return 0
    return last_code or 1


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

    clear_stale_lock()

    # 1) 로컬 변경 스테이징 + 커밋 (ahead 여부와 무관하게 항상 새 변경을 담는다)
    run([GIT, "add", "-A"])
    diff = run([GIT, "diff", "--cached", "--name-only"], check=False)
    changed = [line.strip() for line in (diff.stdout or "").splitlines() if line.strip()]
    # 검증 게이트(D): 깨진 .py/.bat 은 커밋하지 않는다. 편집/마운트 손상이 HEAD까지
    #   오염돼 복구가 어려웠던 사고(매처 main 소실 / bat truncation) 재발 방지.
    import py_compile as _pyc
    _bad = []
    for _rel in changed:
        _r = _rel.strip().strip('"')
        _full = ROOT / _r
        try:
            if _r.endswith(".py"):
                _pyc.compile(str(_full), doraise=True)
            elif _r.endswith(".bat"):
                _b = _full.read_bytes()
                if _b and _b.count(b"\n") != _b.count(b"\r\n"):
                    _bad.append((_r, "LF(CRLF 아님) - cmd 파싱 깨짐"))
        except FileNotFoundError:
            pass
        except Exception as _e:
            _bad.append((_r, (str(_e).splitlines() or [""])[0] or type(_e).__name__))
    if _bad:
        log("")
        log("[ABORT] 검증 실패 - 깨진 파일이 있어 커밋/푸시 중단(HEAD 오염 차단):")
        for _r, _why in _bad:
            log("   X " + _r + ": " + str(_why))
        log("[ABORT] 정상본 복구 후 재시도 (git restore <file>).")
        run([GIT, "reset", "-q"], check=False)
        return 3
    if changed:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        message = f"Update PhoneSpot Codex system {stamp}"
        log("")
        log(f"[commit] {message}  ({len(changed)} files)")
        run([GIT, "commit", "-m", message])
    else:
        log("[info] No new local changes (sync existing commits only).")

    # 2) 원격 통합(merge) — 원격이 앞서 있으면(non-fast-forward) 먼저 합쳐야 push 가능.
    #    --no-edit: 머지 커밋 메시지 에디터가 떠서 멈추는 것 방지.
    log("")
    log("[pull] integrating remote changes (merge) ...")
    pull = run([GIT, "pull", "--no-rebase", "--no-edit"], check=False)
    if pull.returncode:
        log("")
        log("[ERROR] pull(merge) failed - likely a conflict.")
        log("  Fix manually: 'git status' to see conflicts, resolve, 'git add', 'git commit',")
        log("  then run upload again. To undo the merge: 'git merge --abort'.")
        return pull.returncode

    # 3) push
    code = push_with_retry()
    if code:
        log("")
        log("[ERROR] push failed. Check internet / GitHub credentials.")
        return code

    status_script = ROOT / "CODEX_VIDEO_DESK" / "MAINTENANCE" / "codex_github_status.py"
    if status_script.exists():
        subprocess.run([sys.executable, str(status_script)], cwd=str(ROOT))

    log("")
    log("[OK] Upload complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
