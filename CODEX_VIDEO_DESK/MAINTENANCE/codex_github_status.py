# -*- coding: utf-8 -*-
from __future__ import annotations

import json
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
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DESK = ROOT / "CODEX_VIDEO_DESK"
TEMP = DESK / "TEMP"
STATUS_PATH = TEMP / "github_status.json"


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
                timeout=8,
            )
            if result.returncode == 0:
                return candidate
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            continue
    return None


def run(git: str, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [git, *args],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=20,
    )


def write(payload: dict) -> int:
    TEMP.mkdir(parents=True, exist_ok=True)
    payload["checkedAt"] = datetime.now().isoformat(timespec="seconds")
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def main() -> int:
    if not (ROOT / ".git").exists():
        return write({
            "ok": False,
            "state": "not_git",
            "class": "bad",
            "message": "Git 저장소 아님",
            "detail": str(ROOT),
        })

    git = find_git()
    if not git:
        return write({
            "ok": False,
            "state": "git_missing",
            "class": "bad",
            "message": "Git 없음",
            "detail": "Git for Windows 또는 GitHub Desktop 필요",
        })

    branch = run(git, ["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    local = run(git, ["rev-parse", "--short", "HEAD"]).stdout.strip()
    remote_url = run(git, ["remote", "get-url", "origin"]).stdout.strip()
    dirty = [line for line in run(git, ["status", "--short"]).stdout.splitlines() if line.strip()]

    fetch = run(git, ["fetch", "--quiet", "origin"])
    if fetch.returncode != 0:
        return write({
            "ok": False,
            "state": "fetch_failed",
            "class": "warn",
            "message": "GitHub 확인 실패",
            "detail": (fetch.stderr or fetch.stdout or "").strip()[:300],
            "branch": branch,
            "local": local,
            "remote": remote_url,
            "dirty": len(dirty),
        })

    ahead = 0
    behind = 0
    upstream = run(git, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    if upstream.returncode == 0:
        count = run(git, ["rev-list", "--left-right", "--count", "HEAD...@{u}"])
        parts = count.stdout.strip().split()
        if len(parts) == 2:
            ahead, behind = int(parts[0]), int(parts[1])

    if dirty:
        state, cls = "dirty", "warn"
        message = f"로컬 변경 {len(dirty)}개"
        detail = "업데이트 전 변경사항 확인 필요"
    elif behind > 0:
        state, cls = "behind", "warn"
        message = f"업데이트 {behind}개 있음"
        detail = "시스템 업데이트 버튼으로 받을 수 있습니다"
    elif ahead > 0:
        state, cls = "ahead", "warn"
        message = f"푸시 대기 {ahead}개"
        detail = "대표 PC 변경사항을 GitHub에 올려야 합니다"
    else:
        state, cls = "up_to_date", "good"
        message = "최신 상태"
        detail = "GitHub와 동기화됨"

    return write({
        "ok": cls == "good",
        "state": state,
        "class": cls,
        "message": message,
        "detail": detail,
        "branch": branch,
        "local": local,
        "remote": remote_url,
        "ahead": ahead,
        "behind": behind,
        "dirty": len(dirty),
    })


if __name__ == "__main__":
    raise SystemExit(main())
