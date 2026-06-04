from __future__ import annotations

import os
import shutil
from pathlib import Path


ROOT = Path(os.environ.get("PHONESPOT_ROOT", r"C:\Users\di898\Documents\phonespot_cardnews"))
SHORTS = ROOT / "shorts"
DESK = ROOT / "CODEX_VIDEO_DESK"

TARGETS = [
    SHORTS / "scripts" / "codex_enhance_script.py",
    SHORTS / "scripts" / "codex_apply_uploaded_illustrations.py",
    SHORTS / "scripts" / "codex_illustration_scout.py",
]


def first_backup(path: Path) -> Path | None:
    candidates = sorted(
        path.parent.glob(f"{path.name}.bak_illustration_db_*"),
        key=lambda item: item.stat().st_mtime,
    )
    return candidates[0] if candidates else None


def strip_guide_section() -> None:
    path = SHORTS / "codex" / "CODEX_BASELINE.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    marker = "\n\n## Illustration tag DB and recent-use memory"
    if marker in text:
        path.write_text(text.split(marker, 1)[0].rstrip() + "\n", encoding="utf-8")
        print(f"[restore] removed DB guide section: {path}")


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - Rollback Illustration Tag DB")
    print("============================================================")
    restored = 0
    for target in TARGETS:
        backup = first_backup(target)
        if not backup:
            print(f"[skip] backup not found: {target}")
            continue
        shutil.copy2(backup, target)
        restored += 1
        print(f"[restore] {target}")
        print(f"          from {backup.name}")

    for generated in [
        SHORTS / "scripts" / "codex_illustration_db.py",
        SHORTS / "config" / "illustration_tag_db.json",
        SHORTS / "codex" / "illustration_usage_history.json",
        SHORTS / "codex" / "ILLUSTRATION_TAG_DB.md",
        DESK / "11_OPEN_ILLUSTRATION_TAG_DB.bat",
        DESK / "12_REFRESH_ILLUSTRATION_TAG_DB.bat",
    ]:
        if generated.exists():
            generated.unlink()
            print(f"[remove] {generated}")
    strip_guide_section()
    print(f"[DONE] restored files: {restored}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

