from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(os.environ.get("PHONESPOT_ROOT", r"C:\Users\di898\Documents\phonespot_cardnews"))
DESK = ROOT / "CODEX_VIDEO_DESK"
CODEX_TOOLBOX = Path(
    os.environ.get(
        "PHONESPOT_CODEX_TOOLBOX",
        r"C:\Users\di898\Documents\phonespot_cardnews\CODEX_VIDEO_DESK\MAINTENANCE",
    )
)


def write(name: str, text: str) -> None:
    path = DESK / name
    path.write_text(text, encoding="utf-8", newline="\r\n")
    print(f"[write] {path}")


def append_readme() -> None:
    path = DESK / "README.txt"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    marker = "TTS pronunciation and timing controls:"
    if marker in text:
        print("[skip] README already documents TTS controls")
        return
    body = """

TTS pronunciation and timing controls:
8. Run 08_APPLY_TTS_PRONUNCIATION_TIMING.bat once to enable the experimental layer.
9. Run 09_EDIT_TTS_PRONUNCIATION_DICTIONARY.bat to edit speech-only replacements.
10. Run 10_ROLLBACK_TTS_PRONUNCIATION_TIMING.bat if the sample narration becomes worse.

After button 8 is applied, both normal render paths use the layer:
- 01_PREPARE_GPT_PROMPTS.bat -> 02_IMPORT_DOWNLOADS_AND_RENDER.bat
- 03_RENDER_LATEST_WITHOUT_NEW_IMAGES.bat

The authored narration and screen captions stay unchanged.
"""
    path.write_text(text.rstrip() + body + "\n", encoding="utf-8")
    print(f"[write] {path}")


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - Install TTS Desk Buttons")
    print("============================================================")
    DESK.mkdir(parents=True, exist_ok=True)
    write(
        "08_APPLY_TTS_PRONUNCIATION_TIMING.bat",
        f'''@echo off
chcp 65001 > nul
call "{CODEX_TOOLBOX / "RUN_APPLY_CODEX_TTS_PRONUNCIATION_TIMING.bat"}"
''',
    )
    write(
        "09_EDIT_TTS_PRONUNCIATION_DICTIONARY.bat",
        r'''@echo off
chcp 65001 > nul
set "DICT=%~dp0..\shorts\config\tts_pronunciation.json"
if not exist "%DICT%" (
  echo [INFO] Apply button 08 first.
  pause
  exit /b 1
)
start "" notepad "%DICT%"
''',
    )
    write(
        "10_ROLLBACK_TTS_PRONUNCIATION_TIMING.bat",
        f'''@echo off
chcp 65001 > nul
call "{CODEX_TOOLBOX / "RUN_ROLLBACK_CODEX_TTS_PRONUNCIATION_TIMING.bat"}"
''',
    )
    append_readme()
    print("[DONE] TTS controls are now available inside CODEX_VIDEO_DESK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
