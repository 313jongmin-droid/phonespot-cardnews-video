# -*- coding: utf-8 -*-
"""Restore files modified by the most recent list-caption layout install."""
from __future__ import annotations

import os
import shutil
from pathlib import Path


DEFAULT_ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
ROOT = Path(os.environ.get("PHONESPOT_ROOT", str(DEFAULT_ROOT)))
SHORTS = ROOT / "shorts"
FILES = [
    SHORTS / "src" / "components" / "casual" / "chunkUtil.ts",
    SHORTS / "src" / "components" / "casual" / "CasualCaption.tsx",
    SHORTS / "src" / "components" / "casual" / "CasualCard.tsx",
    SHORTS / "scripts" / "validate_codex_korean.py",
    SHORTS / "codex" / "CODEX_BASELINE.md",
]


def restore(path: Path) -> None:
    candidates = sorted(path.parent.glob(f"{path.name}.bak_list_caption_*"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        print(f"[skip] no list-caption backup: {path}")
        return
    source = candidates[0]
    shutil.copy2(source, path)
    print(f"[restore] {path}")
    print(f"          <- {source}")


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - Rollback List Caption Layout Guard")
    print("============================================================")
    for path in FILES:
        restore(path)
    print("[OK] List-caption layout layer restored to its pre-install state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
