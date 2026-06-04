# -*- coding: utf-8 -*-
"""Restore the latest backups created by the fixed-caption rhythm installer."""
from __future__ import annotations

import os
import py_compile
import shutil
import subprocess
from pathlib import Path


DEFAULT_ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
ROOT = Path(os.environ.get("PHONESPOT_ROOT", str(DEFAULT_ROOT)))
SHORTS = ROOT / "shorts"
TARGETS = (
    SHORTS / "src" / "components" / "casual" / "CasualCaption.tsx",
    SHORTS / "src" / "components" / "casual" / "chunkUtil.ts",
    SHORTS / "src" / "components" / "casual" / "CasualCard.tsx",
    SHORTS / "scripts" / "codex_caption_lockstep.py",
    SHORTS / "scripts" / "generate_tts.py",
    SHORTS / "scripts" / "verify_tts_timing.py",
)


def latest_backup(path: Path) -> Path | None:
    matches = sorted(path.parent.glob(f"{path.name}.bak_fixed_caption_rhythm_*"))
    if not matches:
        return None
    return matches[-1]


def main() -> int:
    print("=" * 60)
    print(" PhoneSpot Codex - Roll Back Fixed Caption Rhythm")
    print("=" * 60)
    restore_plan = [(target, latest_backup(target)) for target in TARGETS]
    missing = [target for target, source in restore_plan if source is None]
    if len(missing) == len(TARGETS):
        print("[INFO] Fixed-caption rhythm patch is not installed. Nothing to roll back.")
        return 0
    if missing:
        print("[ERROR] Rollback backups are incomplete. No files were changed.")
        for target in missing:
            print(f"  - missing: {target}")
        return 2
    for target, source in restore_plan:
        assert source is not None
        shutil.copy2(source, target)
        print(f"[restore] {source.name} -> {target}")
    for path in TARGETS[3:]:
        py_compile.compile(str(path), doraise=True)
    if (SHORTS / "tsconfig.json").exists():
        subprocess.run(["cmd", "/c", "npx tsc --noEmit"], cwd=SHORTS, check=True)
    print("[OK] Fixed-caption rhythm patch rolled back.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
