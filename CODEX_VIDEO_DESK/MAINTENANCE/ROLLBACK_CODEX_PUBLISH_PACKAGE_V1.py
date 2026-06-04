# -*- coding: utf-8 -*-
"""Rollback the metadata-only three-channel publish package layer."""
from __future__ import annotations

import os
from pathlib import Path


DEFAULT_ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
ROOT = Path(os.environ.get("PHONESPOT_ROOT", str(DEFAULT_ROOT)))
SHORTS = ROOT / "shorts"
RUNNER = SHORTS / "run_codex_casual.bat"
SCRIPTS = SHORTS / "scripts"
DESK = ROOT / "CODEX_VIDEO_DESK"


def remove_runner_block() -> None:
    text = RUNNER.read_text(encoding="utf-8", errors="replace")
    start = "\necho.\necho ----- Publish package V1: YouTube + Instagram + TikTok -----"
    end = "\necho.\necho ============================================================\necho  DONE. Result: !OUTFILE!"
    if start not in text:
        print("[skip] runner block already absent")
        return
    before, rest = text.split(start, 1)
    _discard, after = rest.split(end, 1)
    RUNNER.write_text(before + end + after, encoding="utf-8", newline="\n")
    print(f"[write] {RUNNER}")


def unlink(path: Path) -> None:
    if path.exists():
        path.unlink()
        print(f"[remove] {path}")


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - Rollback Publish Package V1")
    print("============================================================")
    remove_runner_block()
    unlink(SCRIPTS / "publish_codex_package.py")
    unlink(DESK / "13_REFRESH_LATEST_PUBLISH_PACKAGE.bat")
    unlink(DESK / "14_OPEN_PUBLISH_PACKAGES.bat")
    print("[OK] Publish package V1 runtime hooks removed.")
    print("[INFO] Existing publish package folders were preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
