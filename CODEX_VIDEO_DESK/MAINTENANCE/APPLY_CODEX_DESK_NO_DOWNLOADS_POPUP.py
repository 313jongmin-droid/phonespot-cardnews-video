from __future__ import annotations

import py_compile
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
PREPARE = ROOT / "shorts" / "scripts" / "codex_prepare_illustrations.py"
README = ROOT / "CODEX_VIDEO_DESK" / "README.txt"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


def backup(path: Path) -> None:
    if not path.exists():
        return
    target = path.with_name(f"{path.name}.bak_no_downloads_popup_{STAMP}")
    shutil.copy2(path, target)
    print(f"[backup] {target}")


def patch_prepare() -> None:
    text = PREPARE.read_text(encoding="utf-8")
    original = text
    text = text.replace('DOWNLOADS = Path.home() / "Downloads"\n', "")
    text = text.replace(
        '    if DOWNLOADS.exists():\n'
        '        os.startfile(DOWNLOADS)\n',
        "",
    )
    if text == original:
        print("[skip] prepare script already avoids Downloads popup")
        return
    backup(PREPARE)
    PREPARE.write_text(text, encoding="utf-8", newline="\n")
    print(f"[write] {PREPARE}")


def patch_readme() -> None:
    if not README.exists():
        return
    text = README.read_text(encoding="utf-8", errors="replace")
    updated = text.replace(
        "2. The latest prompt and Downloads folder open automatically.",
        "2. The latest prompt opens automatically.",
    )
    if updated == text:
        print("[skip] README already updated")
        return
    backup(README)
    README.write_text(updated, encoding="utf-8", newline="\n")
    print(f"[write] {README}")


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - Disable Downloads Popup In Step 01")
    print("============================================================")
    if not PREPARE.exists():
        raise RuntimeError(f"prepare script missing: {PREPARE}")
    patch_prepare()
    patch_readme()
    py_compile.compile(str(PREPARE), doraise=True)
    print("[OK] Step 01 now opens only LATEST_PROMPT.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

