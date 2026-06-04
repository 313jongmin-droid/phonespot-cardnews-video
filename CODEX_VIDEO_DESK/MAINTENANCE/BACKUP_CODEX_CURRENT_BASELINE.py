# -*- coding: utf-8 -*-
"""Create a compact reproducible backup of the active Codex Remotion baseline."""
from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path


HERE = Path(__file__).resolve().parent
PHONE = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
SHORTS = PHONE / "shorts"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUPS = HERE.parent / "BACKUPS"
TARGET = BACKUPS / f"CODEX_CURRENT_BASELINE_{STAMP}.zip"

LOCAL_FILES = (
    "RUN_APPLY_CODEX_CURRENT_BASELINE.bat",
    "APPLY_CODEX_KOREAN_CAPTION_GUARD.py",
    "APPLY_CODEX_SOURCE_IMAGE_ONCE_GUARD.py",
    "APPLY_CODEX_VIDEO_DESK.py",
    "APPLY_CODEX_GUIDE_BASELINE.py",
    "APPLY_CODEX_CLEAN_ILLUSTRATION_SCOUT.py",
    "APPLY_CODEX_FAST_ILLUSTRATION_DESK.py",
    "APPLY_CODEX_MASTER_VIDEO_GUIDE.py",
    "APPLY_CODEX_DISABLE_CAPTION_HIGHLIGHT.py",
    "APPLY_CODEX_FIXED_CAPTION_RHYTHM.py",
    "APPLY_CODEX_TTS_CAPTION_LOCKSTEP.py",
    "APPLY_CODEX_RESULTS_PACKAGE_V2.py",
    "RUN_APPLY_CODEX_MASTER_VIDEO_GUIDE.bat",
    "RUN_APPLY_CODEX_DISABLE_CAPTION_HIGHLIGHT.bat",
    "RUN_APPLY_CODEX_FIXED_CAPTION_RHYTHM.bat",
    "ROLLBACK_CODEX_FIXED_CAPTION_RHYTHM.py",
    "RUN_ROLLBACK_CODEX_FIXED_CAPTION_RHYTHM.bat",
    "RUN_APPLY_CODEX_TTS_CAPTION_LOCKSTEP.bat",
    "RUN_APPLY_CODEX_RESULTS_PACKAGE_V2.bat",
    "OPEN_CODEX_VIDEO_DESK.bat",
    "RUN_CODEX_REGRESSION_AUDIT.bat",
    "CODEX_REGRESSION_AUDIT.py",
    "RUN_BACKUP_CODEX_CURRENT_BASELINE.bat",
    "BACKUP_CODEX_CURRENT_BASELINE.py",
    "CLEAN_CODEX_CONFIRMED_JUNK.ps1",
    "RUN_PREVIEW_CODEX_CONFIRMED_JUNK.bat",
    "RUN_DELETE_CODEX_CONFIRMED_JUNK.bat",
    "CODEX_CURRENT_BASELINE_GUIDE.md",
    "CODEX_MASTER_VIDEO_GUIDE.md",
    "CODEX_DISABLE_CAPTION_HIGHLIGHT_GUIDE.md",
    "CODEX_FIXED_CAPTION_RHYTHM_GUIDE.md",
    "CODEX_BASELINE_AUDIT_20260601.md",
    "CODEX_TOKEN_DIET.md",
)

SHARED_FILES = (
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    "run_codex_casual.bat",
)

SHARED_DIRS = (
    "src",
    "codex",
    "harness",
    "logos",
    "public/assets/illustrations",
    "scripts",
)

EXCLUDE_PARTS = {
    "node_modules",
    "out",
    "out_codex",
    "audio",
    "__pycache__",
}


def excluded(path: Path) -> bool:
    if any(part in EXCLUDE_PARTS for part in path.parts):
        return True
    return ".bak" in path.name or path.suffix.lower() in {".mp4", ".mp3", ".zip"}


def add_file(zf: zipfile.ZipFile, source: Path, arcname: str, manifest: list[str]) -> None:
    if source.exists() and source.is_file() and not excluded(source):
        zf.write(source, arcname)
        manifest.append(arcname)


def main() -> int:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    manifest: list[str] = []
    with zipfile.ZipFile(TARGET, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in LOCAL_FILES:
            add_file(zf, HERE / name, f"codex_installer/{name}", manifest)
        for name in SHARED_FILES:
            add_file(zf, SHORTS / name, f"phonespot_cardnews/shorts/{name}", manifest)
        for relative in SHARED_DIRS:
            root = SHORTS / relative
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.is_file() and not excluded(path):
                    arcname = f"phonespot_cardnews/shorts/{path.relative_to(SHORTS).as_posix()}"
                    add_file(zf, path, arcname, manifest)
        zf.writestr(
            "MANIFEST.json",
            json.dumps(
                {
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "purpose": "PhoneSpot Codex Remotion active baseline",
                    "file_count": len(manifest),
                    "files": sorted(manifest),
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
    print(f"[OK] Backup: {TARGET}")
    print(f"[OK] Files : {len(manifest)}")
    print(f"[OK] Size  : {TARGET.stat().st_size / 1024 / 1024:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
