from __future__ import annotations

import os
import subprocess
# 무콘솔 부모(패널 pythonw) 밑에서는 자식 git이 새 콘솔 창을 띄운다(터미널 깜빡임).
# 이 스크립트의 모든 subprocess.run에 CREATE_NO_WINDOW 기본 주입.
if os.name == "nt":
    _NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    _orig_run = subprocess.run
    def _run_no_window(*_a, **_k):
        _k.setdefault("creationflags", _NO_WINDOW)
        return _orig_run(*_a, **_k)
    subprocess.run = _run_no_window
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMP = ROOT / "CODEX_VIDEO_DESK" / "TEMP"
LOG_PATH = TEMP / "github_upload.log"

# 무콘솔(패널) 커밋 hang 방지: git 완전 비대화형(GPG pinentry/에디터/자격증명 프롬프트 차단).
os.environ.setdefault("GIT_TERMINAL_PROMPT", "0")
os.environ["GIT_EDITOR"] = "true"
os.environ["GIT_PAGER"] = "cat"
os.environ["GIT_OPTIONAL_LOCKS"] = "0"


def clear_stale_lock() -> None:
    """.git 잔재 락 정리 (2026-06-22 index.lock -> 2026-07-29 HEAD.lock/ref락 확장).
    60초 이상 묵은 락 = crash/hung 커밋 잔재로 보고 제거. 활성 작업(<60초)은 건드리지 않음.
    hung 커밋이 남기는 HEAD.lock 때문에 이후 커밋이 'cannot lock ref HEAD'로 전부 막히던 것 차단."""
    gitdir = ROOT / ".git"
    locks = [gitdir / "index.lock", gitdir / "HEAD.lock", gitdir / "config.lock"]
    for sub in ("refs", "logs"):
        d = gitdir / sub
        if d.exists():
            locks += list(d.rglob("*.lock"))
    for lock in locks:
        try:
            if not lock.exists():
                continue
            age = time.time() - lock.stat().st_mtime
        except OSError:
            age = 9999
        if age > 60:
            try:
                lock.unlink()
                log(f"[lock] stale {lock.name} removed (age {int(age)}s)")
            except OSError as e:
                log(f"[lock] remove failed {lock.name}: {e}")
        else:
            log(f"[lock] active {lock.name} (age {int(age)}s) - skip")


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


def run(command: list[str], check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess:
    log("")
    log("[cmd] " + " ".join(command))
    # ★ stdout을 파이프가 아니라 임시파일로 캡처한다. git-lfs filter-process 등 손자 프로세스가
    #   git의 stdout 파이프 핸들을 상속·유지하면, 파이프 캡처(subprocess.run stdout=PIPE)는 EOF를
    #   영원히 못 받아 무창 패널에서 deadlock. 파일 캡처는 git 종료 즉시 반환하므로 교착이 없다.
    import tempfile as _tempfile
    with _tempfile.TemporaryFile() as _fh:
        try:
            result = subprocess.run(command, cwd=str(ROOT), stdout=_fh, stderr=subprocess.STDOUT, timeout=timeout)
        except subprocess.TimeoutExpired:
            log(f"[ERROR] command timed out after {timeout}s: " + " ".join(command))
            raise SystemExit(124)
        _fh.seek(0)
        out = _fh.read().decode("utf-8", "replace")
    result.stdout = out
    for line in out.splitlines():
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
        result = run([GIT, "push"], check=False, timeout=120)
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
        # 패널(무콘솔) 커밋에서 git 훅이 hang(pre-commit 게이트·post-commit 텔레그램) → 이 자동 업로드는
        # 훅 비활성으로 커밋한다(존재하지 않는 hooksPath). 문법/BOM 게이트는 cmd 커밋(콘솔)에서 유지됨.
        _no_hooks = str(ROOT / ".git" / "_disabled_hooks_nonexistent")
        run([GIT, "-c", "core.hooksPath=" + _no_hooks, "-c", "commit.gpgsign=false", "commit", "--no-verify", "-m", message], timeout=90)
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
