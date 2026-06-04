# -*- coding: utf-8 -*-
"""Install display-only sentence-period removal for Codex Remotion captions."""
from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path


DEFAULT_ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
ROOT = Path(os.environ.get("PHONESPOT_ROOT", str(DEFAULT_ROOT)))
SHORTS = ROOT / "shorts"
CHUNK_UTIL = SHORTS / "src" / "components" / "casual" / "chunkUtil.ts"
BASELINE = SHORTS / "codex" / "CODEX_BASELINE.md"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

MARKER = "// Display-caption punctuation guard:"
INSERT_BEFORE = "export function formatCaptionLines(text: string, maxLineChars = 18, maxLines = 3): string {"
OLD_CLEAN = '  const clean = text.replace(/\\n/g, " ").trim();'
NEW_CLEAN = '  const clean = stripDisplaySentencePeriods(text).replace(/\\n/g, " ").trim();'

HELPER = r'''
// Display-caption punctuation guard:
// - Hide sentence periods on screen for a cleaner Shorts caption style.
// - Keep decimal/version separators such as `26.6` and `1.5`.
// - TTS and authored narration are not modified.
export const stripDisplaySentencePeriods = (value: string) =>
  value.replace(/\./g, (dot, offset, source) => {
    const before = source[offset - 1] || "";
    const after = source[offset + 1] || "";
    return /\d/.test(before) && /\d/.test(after) ? dot : "";
  });

'''

BASELINE_NOTE = """
## Display-caption period guard

- 화면 청크에서는 문장부호 마침표 `.`를 표시하지 않습니다.
- `iOS 26.6`, `1.5배`처럼 숫자 사이의 소수점과 버전 구분점은 유지합니다.
- 이 규칙은 화면 표시 전용입니다. TTS와 작성된 나레이션 원문은 변경하지 않습니다.
"""


def backup(path: Path) -> None:
    if not path.exists():
        return
    target = path.with_name(f"{path.name}.bak_hide_periods_{STAMP}")
    shutil.copy2(path, target)
    print(f"[backup] {target}")


def append_once(path: Path, text: str, marker: str) -> None:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in current:
        print(f"[skip] guide already contains: {marker}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(current.rstrip() + "\n\n" + text.strip() + "\n", encoding="utf-8")
    print(f"[write] {path}")


def patch_chunk_util() -> None:
    if not CHUNK_UTIL.exists():
        raise RuntimeError(f"chunkUtil.ts not found: {CHUNK_UTIL}")
    text = CHUNK_UTIL.read_text(encoding="utf-8")
    if MARKER in text and NEW_CLEAN in text:
        print("[skip] display-caption period guard already installed")
        return
    if INSERT_BEFORE not in text:
        raise RuntimeError("chunkUtil.ts patch anchor missing: formatCaptionLines")
    if OLD_CLEAN not in text and NEW_CLEAN not in text:
        raise RuntimeError("chunkUtil.ts patch anchor missing: clean line")
    backup(CHUNK_UTIL)
    if MARKER not in text:
        text = text.replace(INSERT_BEFORE, HELPER + INSERT_BEFORE, 1)
    text = text.replace(OLD_CLEAN, NEW_CLEAN, 1)
    CHUNK_UTIL.write_text(text, encoding="utf-8")
    print(f"[write] {CHUNK_UTIL}")


def main() -> int:
    print("=" * 60)
    print(" PhoneSpot Codex - Hide Caption Sentence Periods")
    print("=" * 60)
    patch_chunk_util()
    append_once(BASELINE, BASELINE_NOTE, "## Display-caption period guard")
    print("[OK] Screen captions hide sentence periods; decimal/version dots remain.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
