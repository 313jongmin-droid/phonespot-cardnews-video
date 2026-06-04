# -*- coding: utf-8 -*-
"""Install a one-folder Codex video workbench for daily PhoneSpot use."""
from __future__ import annotations

import py_compile
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
SHORTS = ROOT / "shorts"
SCRIPTS = SHORTS / "scripts"
RUNNER = SHORTS / "run_codex_casual.bat"
HELPER = SCRIPTS / "codex_refresh_workbench.py"
MEMORY = SHORTS / "codex" / "CODEX_MEMORY.md"
PATCH_LOG = SHORTS / "codex" / "codex_patch_log.md"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

HELPER_CODE = r'''# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
CARDNEWS = ROOT / "cardnews"
DESK = ROOT / "CODEX_VIDEO_DESK"
ILLUST = DESK / "ILLUSTRATION_DROP"
RESULTS = DESK / "RESULTS"


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def make_junction(link: Path, target: Path) -> bool:
    target.mkdir(parents=True, exist_ok=True)
    if link.exists():
        return True
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode == 0 and link.exists()


def setup_buttons() -> None:
    DESK.mkdir(parents=True, exist_ok=True)
    ILLUST.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    ILLUST.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (DESK / "TEMP" / "_raw").mkdir(parents=True, exist_ok=True)
    write(
        DESK / "01_RUN_CODEX_REMOTION.bat",
        '@echo off\r\ncd /d "%~dp0..\\shorts"\r\ncall run_codex_casual.bat\r\n',
    )
    write(
        DESK / "02_OPEN_LATEST_PROMPT.bat",
        '@echo off\r\nstart "" notepad "%~dp0LATEST_PROMPT.md"\r\n',
    )
    write(
        DESK / "03_OPEN_ILLUSTRATION_DROP.bat",
        '@echo off\r\nstart "" explorer "' + str(ILLUST) + '"\r\n',
    )
    write(
        DESK / "04_OPEN_RESULTS.bat",
        '@echo off\r\nstart "" explorer "' + str(RESULTS) + '"\r\n',
    )
    write(
        DESK / "05_REFRESH_LATEST_PROMPT.bat",
        '@echo off\r\ncd /d "%~dp0..\\shorts"\r\npython scripts\\codex_refresh_workbench.py\r\npause\r\n',
    )
    write(
        DESK / "README.txt",
        """PhoneSpot Codex Video Desk

01_RUN_CODEX_REMOTION.bat
  Render one Codex Remotion short.

02_OPEN_LATEST_PROMPT.bat
  Open the latest GPT Plus illustration prompt report.

03_OPEN_ILLUSTRATION_DROP.bat
  Save generated PNG illustrations here using the requested filename.
  This points to the real Remotion illustration library.

04_OPEN_RESULTS.bat
  Open completed Codex MP4 files and copied reports.

05_REFRESH_LATEST_PROMPT.bat
  Refresh the latest prompt file manually if needed.
""",
    )


def latest_slug() -> str | None:
    candidates = sorted(
        CARDNEWS.glob("output/*/codex_illustration_requests.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0].parent.name if candidates else None


def refresh(slug: str | None) -> None:
    setup_buttons()
    selected = slug or latest_slug()
    if not selected:
        write(DESK / "LATEST_PROMPT.md", "# Codex Illustration Requests\n\nNo prompt report is available yet.\n")
        write(DESK / "LATEST_SLUG.txt", "none\n")
        return
    source_md = CARDNEWS / "output" / selected / "codex_illustration_requests.md"
    source_json = CARDNEWS / "output" / selected / "codex_illustration_requests.json"
    if source_md.exists():
        shutil.copy2(source_md, DESK / "LATEST_PROMPT.md")
    else:
        write(
            DESK / "LATEST_PROMPT.md",
            f"# Codex Illustration Requests: {selected}\n\nNo new illustration request was generated.\n",
        )
    if source_json.exists():
        shutil.copy2(source_json, DESK / "LATEST_PROMPT.json")
    elif (DESK / "LATEST_PROMPT.json").exists():
        (DESK / "LATEST_PROMPT.json").unlink()
    write(DESK / "LATEST_SLUG.txt", selected + "\n")
    print(f"[workbench] desk: {DESK}")
    print(f"[workbench] latest prompt: {DESK / 'LATEST_PROMPT.md'}")
    print(f"[workbench] illustration drop: {DESK / 'ILLUSTRATION_DROP'}")
    print(f"[workbench] results: {DESK / 'RESULTS'}")


if __name__ == "__main__":
    refresh(sys.argv[1] if len(sys.argv) > 1 else None)
'''


def backup(path: Path) -> Path:
    target = path.with_name(path.name + f".bak_video_desk_{STAMP}")
    shutil.copy2(path, target)
    print(f"[backup] {target}")
    return target


def append_once(path: Path, marker: str, body: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in text:
        return
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text + "\n" + body.rstrip() + "\n", encoding="utf-8")
    print(f"[note] {path}")


def patch_runner() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    anchor = "python scripts\\codex_illustration_scout.py !SLUG!\nif errorlevel 1 goto :fail"
    replacement = (
        "python scripts\\codex_illustration_scout.py !SLUG!\n"
        "if errorlevel 1 goto :fail\n"
        "python scripts\\codex_refresh_workbench.py !SLUG!\n"
        "if errorlevel 1 goto :fail"
    )
    if replacement in text:
        print("[skip] runner already refreshes Codex video desk")
        return
    if anchor not in text:
        raise RuntimeError("Codex runner workbench anchor missing")
    backup(RUNNER)
    RUNNER.write_text(text.replace(anchor, replacement, 1), encoding="utf-8")
    print(f"[write] {RUNNER}")


def main() -> int:
    if not RUNNER.exists():
        raise RuntimeError("PhoneSpot Codex runner not found")
    HELPER.write_text(HELPER_CODE, encoding="utf-8")
    print(f"[write] {HELPER}")
    py_compile.compile(str(HELPER), doraise=True)
    patch_runner()
    subprocess.run(["python", str(HELPER)], check=True)
    append_once(
        MEMORY,
        "## 29. Codex video desk",
        """## 29. Codex video desk
- Daily Codex video work uses `CODEX_VIDEO_DESK/`.
- The desk contains the render button, latest GPT Plus prompt, illustration drop folder, and result folder.
- `ILLUSTRATION_DROP` points to the real Remotion illustration library. Save PNGs there with the requested filename.
- Codex runner refreshes `LATEST_PROMPT.md` after every illustration scout run.""",
    )
    append_once(
        PATCH_LOG,
        "## 2026-06-01 - Codex video desk",
        """## 2026-06-01 - Codex video desk
- Added a one-folder daily workbench at `CODEX_VIDEO_DESK/`.
- Added render, latest-prompt, illustration-drop, result, and manual-refresh buttons.
- Codex runner now refreshes the latest prompt report immediately after scouting illustrations.""",
    )
    print("[done] Codex video desk installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
