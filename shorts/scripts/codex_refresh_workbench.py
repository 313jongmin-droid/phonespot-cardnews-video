# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
CARDNEWS = ROOT / "cardnews"
DESK = ROOT / "CODEX_VIDEO_DESK"
ILLUST = DESK / "ILLUSTRATION_DROP"
RESULTS = DESK / "RESULTS"


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def is_junction(path: Path) -> bool:
    checker = getattr(path, "is_junction", None)
    return bool(checker and checker())


def remove_link_only(path: Path) -> None:
    if not path.exists():
        return
    if is_junction(path):
        path.rmdir()
        return
    if path.is_symlink():
        path.unlink()
        return
    print(f"[WARN] Keeping real folder instead of removing it: {path}")


def make_junction(link: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    if link.exists():
        try:
            if link.resolve() == target.resolve():
                return
        except OSError:
            pass
        if is_junction(link) or link.is_symlink():
            remove_link_only(link)
        elif link.is_dir() and not any(link.iterdir()):
            for attempt in range(5):
                try:
                    link.rmdir()
                    break
                except OSError:
                    if attempt == 4:
                        raise
                    time.sleep(0.4)
        else:
            raise RuntimeError(f"Cannot replace non-empty real folder with junction: {link}")
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=False)


def latest_slug() -> str | None:
    rows = sorted(
        CARDNEWS.glob("output/*/codex_illustration_requests.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return rows[0].parent.name if rows else None


def refresh(slug: str | None) -> None:
    DESK.mkdir(parents=True, exist_ok=True)
    ILLUST.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (DESK / "TEMP" / "_raw").mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(SHORTS / "scripts" / "sync_codex_illustrations.py")], check=True)
    remove_link_only(DESK / "OUT_CODEX")
    selected = slug or latest_slug()
    if not selected:
        write(DESK / "LATEST_PROMPT.md", "# Codex Illustration Requests\n\nNo prompt report is available yet.\n")
        write(DESK / "LATEST_PROMPT.json", json.dumps({"requests": []}, ensure_ascii=False, indent=2))
        write(DESK / "LATEST_SLUG.txt", "none\n")
        return
    source_md = CARDNEWS / "output" / selected / "codex_illustration_requests.md"
    source_json = CARDNEWS / "output" / selected / "codex_illustration_requests.json"
    if source_md.exists():
        shutil.copy2(source_md, DESK / "LATEST_PROMPT.md")
    else:
        write(DESK / "LATEST_PROMPT.md", f"# Codex Illustration Requests: {selected}\n\nNo new illustration request was generated.\n")
    if source_json.exists():
        shutil.copy2(source_json, DESK / "LATEST_PROMPT.json")
    else:
        write(DESK / "LATEST_PROMPT.json", json.dumps({"slug": selected, "requests": []}, ensure_ascii=False, indent=2))
    write(DESK / "LATEST_SLUG.txt", selected + "\n")
    print(f"[workbench] latest slug: {selected}")
    print(f"[workbench] latest prompt: {DESK / 'LATEST_PROMPT.md'}")
    print(f"[workbench] results: {DESK / 'RESULTS'}")


if __name__ == "__main__":
    refresh(sys.argv[1] if len(sys.argv) > 1 else None)
