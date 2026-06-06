# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
SCRIPTS = SHORTS / "scripts"
DESK = ROOT / "CODEX_VIDEO_DESK"


def run(script: str, *args: str) -> None:
    command = [sys.executable, str(SCRIPTS / script), *args]
    result = subprocess.run(command)
    if result.returncode:
        raise SystemExit(result.returncode)


def select_slug() -> str:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "list_slugs.py")],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=True,
    )
    print("")
    print("Select a news folder by number:")
    print("------------------------------------------------------------")
    print(result.stdout.rstrip())
    print("------------------------------------------------------------")
    number = input("Enter number: ").strip()
    if not number:
        raise SystemExit("No number entered.")
    slug = subprocess.run(
        [sys.executable, str(SCRIPTS / "get_slug.py"), number],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=True,
    ).stdout.strip()
    if not slug:
        raise SystemExit("Invalid number.")
    return slug


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else select_slug()
    print("")
    print(f"[prepare] slug: {slug}")
    run("build_script.py", slug)
    run("codex_enhance_script.py", slug)
    run("codex_apply_uploaded_illustrations.py", slug)
    run("codex_illustration_scout.py", slug)
    run("codex_refresh_workbench.py", slug)
    prompt = DESK / "LATEST_PROMPT.md"
    if prompt.exists() and os.environ.get("PHONESPOT_NO_OPEN") != "1":
        try:
            os.startfile(prompt)
        except OSError as exc:
            print(f"[WARN] Prompt report could not be opened automatically: {exc}")
    print("")
    print("[OK] Prompt report is ready.")
    print("[NEXT] Generate GPT Plus illustrations in report order and download them.")
    print("[NEXT] Then run 02_IMPORT_DOWNLOADS_AND_RENDER.bat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
