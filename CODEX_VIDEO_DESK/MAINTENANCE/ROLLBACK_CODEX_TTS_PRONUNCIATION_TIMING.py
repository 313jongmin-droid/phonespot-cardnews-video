from __future__ import annotations

import os
import shutil
from pathlib import Path


ROOT = Path(os.environ.get("PHONESPOT_ROOT", r"C:\Users\di898\Documents\phonespot_cardnews"))
SHORTS = ROOT / "shorts"

TARGETS = [
    SHORTS / "scripts" / "generate_tts.py",
    SHORTS / "src" / "components" / "casual" / "chunkUtil.ts",
    SHORTS / "src" / "components" / "casual" / "CasualCaption.tsx",
    SHORTS / "src" / "components" / "casual" / "CasualCard.tsx",
    SHORTS / "run_codex_casual.bat",
]


def latest_backup(path: Path) -> Path | None:
    candidates = sorted(
        path.parent.glob(f"{path.name}.bak_tts_timing_*"),
        key=lambda item: item.stat().st_mtime,
    )
    # The first backup is the state before this layer was installed.
    # Later backups may already contain the layer after an idempotency re-run.
    return candidates[0] if candidates else None


def strip_guide_section() -> None:
    path = SHORTS / "codex" / "CODEX_BASELINE.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    marker = "\n\n## TTS pronunciation and timing layer"
    if marker in text:
        path.write_text(text.split(marker, 1)[0].rstrip() + "\n", encoding="utf-8")
        print(f"[restore] removed TTS guide section: {path}")


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - Rollback TTS Pronunciation + Timing Layer")
    print("============================================================")
    restored = 0
    for target in TARGETS:
        backup = latest_backup(target)
        if not backup:
            print(f"[skip] backup not found: {target}")
            continue
        shutil.copy2(backup, target)
        restored += 1
        print(f"[restore] {target}")
        print(f"          from {backup.name}")

    for generated in [
        SHORTS / "scripts" / "verify_tts_timing.py",
        SHORTS / "config" / "tts_pronunciation.json",
        SHORTS / "public" / "audio" / "tts_manifest.json",
    ]:
        if generated.exists():
            generated.unlink()
            print(f"[remove] {generated}")
    strip_guide_section()
    print(f"[DONE] restored files: {restored}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
