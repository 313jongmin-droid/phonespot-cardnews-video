# -*- coding: utf-8 -*-
"""Roll back the experimental Korean caption compiler V2."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(os.environ.get("PHONESPOT_ROOT", r"C:\Users\di898\Documents\phonespot_cardnews"))
SHORTS = ROOT / "shorts"
TARGETS = (
    SHORTS / "scripts" / "codex_caption_lockstep.py",
    SHORTS / "src" / "components" / "casual" / "chunkUtil.ts",
    SHORTS / "run_codex_casual.bat",
)
VALIDATOR = SHORTS / "scripts" / "validate_caption_compiler_v2.py"
SUFFIX = ".bak_caption_compiler_v2_"


def latest_backup(path: Path) -> Path | None:
    backups = sorted(path.parent.glob(path.name + SUFFIX + "*"), key=lambda item: item.stat().st_mtime)
    return backups[-1] if backups else None


def typecheck() -> None:
    if os.environ.get("PHONESPOT_SKIP_TSC") == "1":
        print("[skip] TypeScript check disabled for isolated fixture")
        return
    result = subprocess.run(["cmd", "/c", "npx.cmd", "tsc", "--noEmit"], cwd=SHORTS)
    if result.returncode != 0:
        raise RuntimeError("TypeScript check failed after rollback")


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - Roll Back Korean Caption Compiler V2")
    print("============================================================")
    plan = [(target, latest_backup(target)) for target in TARGETS]
    missing = [target for target, source in plan if source is None]
    if len(missing) == len(TARGETS):
        print("[INFO] Korean caption compiler V2 is not installed. Nothing to roll back.")
        return 0
    if missing:
        print("[ERROR] Rollback backups are incomplete. No files were changed.")
        for path in missing:
            print(f"  - {path}")
        return 2
    for target, source in plan:
        assert source is not None
        shutil.copy2(source, target)
        print(f"[restore] {target}")
    if VALIDATOR.exists():
        VALIDATOR.unlink()
        print(f"[delete] {VALIDATOR}")
    typecheck()
    print("[OK] Korean caption compiler V2 rolled back.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
