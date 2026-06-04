# -*- coding: utf-8 -*-
"""Rollback display-only sentence-period removal for Codex Remotion captions."""
from __future__ import annotations

import os
from pathlib import Path


DEFAULT_ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
ROOT = Path(os.environ.get("PHONESPOT_ROOT", str(DEFAULT_ROOT)))
CHUNK_UTIL = ROOT / "shorts" / "src" / "components" / "casual" / "chunkUtil.ts"

HELPER_START = "// Display-caption punctuation guard:"
HELPER_END = "export function formatCaptionLines(text: string, maxLineChars = 18, maxLines = 3): string {"
NEW_CLEAN = '  const clean = stripDisplaySentencePeriods(text).replace(/\\n/g, " ").trim();'
OLD_CLEAN = '  const clean = text.replace(/\\n/g, " ").trim();'


def main() -> int:
    if not CHUNK_UTIL.exists():
        raise RuntimeError(f"chunkUtil.ts not found: {CHUNK_UTIL}")
    text = CHUNK_UTIL.read_text(encoding="utf-8")
    if HELPER_START not in text:
        print("[skip] display-caption period guard is not installed")
        return 0
    start = text.index(HELPER_START)
    end = text.index(HELPER_END, start)
    text = text[:start] + text[end:]
    text = text.replace(NEW_CLEAN, OLD_CLEAN, 1)
    CHUNK_UTIL.write_text(text, encoding="utf-8")
    print(f"[write] {CHUNK_UTIL}")
    print("[OK] Caption period guard rolled back.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
