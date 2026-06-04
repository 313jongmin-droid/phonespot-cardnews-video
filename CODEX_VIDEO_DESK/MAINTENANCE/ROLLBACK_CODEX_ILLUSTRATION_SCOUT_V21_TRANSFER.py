# -*- coding: utf-8 -*-
"""Roll back Illustration Scout V2.1 transfer pack."""
from __future__ import annotations

import os
import shutil
from pathlib import Path


ROOT = Path(os.environ.get("PHONESPOT_ROOT", r"C:\Users\di898\Documents\phonespot_cardnews"))
SHORTS = ROOT / "shorts"
TARGETS = (
    SHORTS / "scripts" / "codex_illustration_scout.py",
    SHORTS / "scripts" / "codex_illustration_db.py",
)
SUFFIX = ".bak_illustration_scout_v21_"


def latest_backup(path: Path) -> Path | None:
    rows = sorted(path.parent.glob(path.name + SUFFIX + "*"), key=lambda item: item.stat().st_mtime)
    return rows[-1] if rows else None


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - Roll Back Illustration Scout V2.1")
    print("============================================================")
    plan = [(target, latest_backup(target)) for target in TARGETS]
    missing = [target for target, source in plan if source is None]
    if missing:
        print("[ERROR] Rollback backups are incomplete. No files were changed.")
        for path in missing:
            print(f"  - {path}")
        return 2
    for target, source in plan:
        assert source is not None
        shutil.copy2(source, target)
        print(f"[restore] {target}")
    print("[OK] Illustration Scout V2.1 rolled back.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
