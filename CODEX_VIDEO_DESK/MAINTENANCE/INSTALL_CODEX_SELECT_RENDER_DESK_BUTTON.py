# -*- coding: utf-8 -*-
"""Add a safe desk wrapper for the interactive Codex Remotion runner."""
from __future__ import annotations

import os
from pathlib import Path


DEFAULT_ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
ROOT = Path(os.environ.get("PHONESPOT_ROOT", str(DEFAULT_ROOT)))
DESK = ROOT / "CODEX_VIDEO_DESK"
RUNNER = ROOT / "shorts" / "run_codex_casual.bat"
README = DESK / "README.txt"
BUTTON = DESK / "15_SELECT_AND_RENDER_EXISTING.bat"


BUTTON_TEXT = r'''@echo off
chcp 65001 > nul
cd /d "%~dp0..\shorts"
call run_codex_casual.bat
'''


README_APPEND = r'''

Direct render selection:
15. Run 15_SELECT_AND_RENDER_EXISTING.bat to choose any existing slug and render it.
'''


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - Desk Select-And-Render Button")
    print("============================================================")
    if not RUNNER.exists():
        raise RuntimeError(f"Codex runner missing: {RUNNER}")
    DESK.mkdir(parents=True, exist_ok=True)
    BUTTON.write_text(BUTTON_TEXT.rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"[write] {BUTTON}")

    if README.exists():
        text = README.read_text(encoding="utf-8", errors="replace")
        if "15_SELECT_AND_RENDER_EXISTING.bat" not in text:
            README.write_text(text.rstrip() + "\n" + README_APPEND.strip() + "\n", encoding="utf-8", newline="\n")
            print(f"[write] {README}")
        else:
            print("[skip] README already documents button 15")

    print("[OK] Use CODEX_VIDEO_DESK\\15_SELECT_AND_RENDER_EXISTING.bat")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
