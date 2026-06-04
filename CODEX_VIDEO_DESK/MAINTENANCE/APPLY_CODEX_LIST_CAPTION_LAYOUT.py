# -*- coding: utf-8 -*-
"""Install a global list-caption layout guard for Codex Remotion shorts."""
from __future__ import annotations

import os
import py_compile
import shutil
from datetime import datetime
from pathlib import Path


DEFAULT_ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
ROOT = Path(os.environ.get("PHONESPOT_ROOT", str(DEFAULT_ROOT)))
SHORTS = ROOT / "shorts"
CASUAL = SHORTS / "src" / "components" / "casual"
CHUNK_UTIL = CASUAL / "chunkUtil.ts"
CAPTION = CASUAL / "CasualCaption.tsx"
CARD = CASUAL / "CasualCard.tsx"
VALIDATOR = SHORTS / "scripts" / "validate_codex_korean.py"
BASELINE = SHORTS / "codex" / "CODEX_BASELINE.md"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


CHUNK_HELPERS = r'''
// List-caption guard:
// - Keep markers such as `3)` attached to their item text.
// - Preserve the original number of screen chunks so manual visuals and timing stay aligned.
// - Estimate display width more closely than raw character count for mixed Korean/ASCII captions.
const LIST_MARKER_AT_END = /(?:^|\s)(\d{1,2}[\)\.])\s*$/;
const LIST_MARKER_ONLY = /^\s*(\d{1,2}[\)\.])\s*$/;
const NUMBERED_LIST_MARKER = /(?:^|\s)(\d{1,2}\))\s*/g;
const CONTAINS_NUMBERED_LIST_MARKER = /(?:^|\s)\d{1,2}\)\s*/;
const STARTS_NUMBERED_LIST = /^\s*1\)\s*/;
const ENDS_WITH_SENTENCE_MARK = /[.!?\u3002\uFF01\uFF1F]\s*$/;

const estimateDisplayUnits = (value: string) => {
  let units = 0;
  for (const ch of value) {
    if (/\s/.test(ch)) {
      units += 0.34;
    } else if (/[\uAC00-\uD7A3\u3131-\u318E\u4E00-\u9FFF]/.test(ch)) {
      units += 1;
    } else if (/[A-Za-z0-9]/.test(ch)) {
      units += 0.6;
    } else {
      units += 0.46;
    }
  }
  return units;
};

const repairOrphanListMarkers = (chunks: string[] = []): string[] => {
  const repaired = chunks.map((chunk) => String(chunk || "").trim());

  for (let idx = 0; idx < repaired.length - 1; idx++) {
    const current = repaired[idx];
    const next = repaired[idx + 1];
    const match = current.match(LIST_MARKER_AT_END);
    if (!match || !next || LIST_MARKER_ONLY.test(next)) {
      continue;
    }
    const marker = match[1];
    const currentWithoutMarker = current.slice(0, match.index).trim();
    repaired[idx] = currentWithoutMarker || current;
    repaired[idx + 1] = `${marker} ${next}`.trim();
  }

  return repaired;
};

const parseNumberedItems = (text: string): string[] => {
  const matches = Array.from(text.matchAll(NUMBERED_LIST_MARKER));
  if (matches.length < 2 || matches[0][1] !== "1)") {
    return [];
  }
  return matches.map((match, idx) => {
    const start = (match.index || 0) + match[0].length;
    const end = idx + 1 < matches.length ? matches[idx + 1].index || text.length : text.length;
    return `${match[1]} ${text.slice(start, end).trim()}`.trim();
  });
};

const rebalanceNumberedLists = (chunks: string[]): string[] => {
  const repaired = [...chunks];

  for (let start = 0; start < repaired.length; start++) {
    if (!STARTS_NUMBERED_LIST.test(repaired[start])) {
      continue;
    }
    let end = start;
    while (end + 1 < repaired.length && CONTAINS_NUMBERED_LIST_MARKER.test(repaired[end + 1])) {
      end += 1;
    }

    let combined = repaired.slice(start, end + 1).join(" ").trim();
    let items = parseNumberedItems(combined);
    if (!items.length) {
      continue;
    }

    const lastItem = items[items.length - 1] || "";
    const continuation = repaired[end + 1] || "";
    if (
      !ENDS_WITH_SENTENCE_MARK.test(lastItem) &&
      continuation &&
      !CONTAINS_NUMBERED_LIST_MARKER.test(continuation)
    ) {
      end += 1;
      combined = repaired.slice(start, end + 1).join(" ").trim();
      items = parseNumberedItems(combined);
    }

    const slots = end - start + 1;
    if (items.length < slots || slots < 2) {
      continue;
    }
    let itemCursor = 0;
    for (let slot = 0; slot < slots; slot++) {
      const remainingItems = items.length - itemCursor;
      const remainingSlots = slots - slot;
      const take = Math.max(1, Math.ceil(remainingItems / remainingSlots));
      repaired[start + slot] = items.slice(itemCursor, itemCursor + take).join(" ");
      itemCursor += take;
    }
    start = end;
  }

  return repaired;
};

export const repairListChunkBoundaries = (chunks: string[] = []): string[] =>
  rebalanceNumberedLists(repairOrphanListMarkers(chunks));
'''


PY_VALIDATOR_HELPER = r'''

LIST_MARKER_AT_END = re.compile(r"(?:^|\s)(\d{1,2}[\)\.])\s*$")
LIST_MARKER_ONLY = re.compile(r"^\s*(\d{1,2}[\)\.])\s*$")


def validate_list_caption_layout(data: dict) -> None:
    """Allow runtime-repairable list splits and block unrecoverable orphan markers."""
    errors: list[str] = []
    repairs: list[str] = []
    sections = [("hook", data.get("hook") or {})]
    sections.extend((str(item.get("id") or f"fact_{idx + 1}"), item) for idx, item in enumerate(data.get("facts") or []))
    sections.append(("cta", data.get("cta") or {}))

    for section_name, section in sections:
        for field in ("caption_chunks", "display_chunks"):
            chunks = [str(chunk or "").strip() for chunk in (section.get(field) or [])]
            for idx, chunk in enumerate(chunks):
                match = LIST_MARKER_AT_END.search(chunk)
                if not match:
                    continue
                marker = match.group(1)
                if idx + 1 >= len(chunks) or not chunks[idx + 1].strip():
                    errors.append(f"{section_name}.{field}[{idx}]: orphan list marker `{marker}` has no following item")
                else:
                    repairs.append(f"{section_name}.{field}[{idx}] `{marker}` -> next chunk")

    if errors:
        raise ValueError("List-caption layout contract failed\n- " + "\n- ".join(errors))
    if repairs:
        print(f"[list_caption_guard] runtime repairs: {len(repairs)}")
        for repair in repairs[:8]:
            print(f"  - {repair}")
'''


BASELINE_APPEND = r'''

## List-caption layout guard

- Numbered list markers such as `3)` stay attached to the following item text.
- Runtime repair preserves the number of caption chunks, TTS windows, and manual visual mappings.
- Mixed Korean, ASCII, punctuation, and numbers use a weighted display-width estimate instead of raw character count only.
- The Korean preflight allows repairable boundary splits and blocks unrecoverable orphan list markers before rendering.
- This is a global rule for future videos, not a slug-specific exception.
'''


def backup(path: Path) -> None:
    if not path.exists():
        return
    target = path.with_name(f"{path.name}.bak_list_caption_{STAMP}")
    shutil.copy2(path, target)
    print(f"[backup] {target}")


def write(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8", newline="\n")
    print(f"[write] {path}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"patch anchor missing: {label}")
    return text.replace(old, new, 1)


def patch_chunk_util() -> None:
    text = CHUNK_UTIL.read_text(encoding="utf-8")
    if "export const repairListChunkBoundaries" in text:
        print("[skip] chunkUtil list-caption helpers already installed")
        return
    original = text
    text = replace_once(
        text,
        'const countChars = (value: string) => value.replace(/\\s/g, "").length;\n',
        'const countChars = (value: string) => value.replace(/\\s/g, "").length;\n' + CHUNK_HELPERS + "\n",
        "chunkUtil helper insertion",
    )
    text = replace_once(
        text,
        '  let output = text;\n',
        '  let output = text.replace(/(^|\\s)(\\d{1,2}[\\)\\.])\\s+([^\\s]+)/g, (_match, prefix, marker, word) => {\n'
        '    const key = `__PS${protectedTokens.length}__`;\n'
        '    protectedTokens.push(`${marker}\\u00A0${word}`);\n'
        '    return `${prefix}${key}`;\n'
        '  });\n',
        "protect list item head",
    )
    text = replace_once(
        text,
        "  const lengths = lines.map(countChars);\n",
        "  const lengths = lines.map(estimateDisplayUnits);\n",
        "weighted line score",
    )
    text = replace_once(
        text,
        "  if (countChars(clean) <= maxLineChars) {\n",
        "  if (estimateDisplayUnits(clean) <= maxLineChars) {\n",
        "weighted fast path",
    )
    if text != original:
        backup(CHUNK_UTIL)
        write(CHUNK_UTIL, text)


def patch_caption() -> None:
    text = CAPTION.read_text(encoding="utf-8")
    if "repairListChunkBoundaries" in text:
        print("[skip] CasualCaption list repair already installed")
        return
    original = text
    text = replace_once(
        text,
        'import { chunkIndexFromList, formatCaptionLines } from "./chunkUtil";\n',
        'import { chunkIndexFromList, formatCaptionLines, repairListChunkBoundaries } from "./chunkUtil";\n',
        "CasualCaption import",
    )
    text = replace_once(
        text,
        '  const list = chunks && chunks.length ? chunks : [""];\n'
        '  const idx = chunkIndexFromList(list, frame, durFrames, timingWeights);\n'
        '  const current = list[idx] || "";\n'
        '  const displaySource = displayChunks[idx] || current;\n',
        '  const list = repairListChunkBoundaries(chunks && chunks.length ? chunks : [""]);\n'
        '  const repairedDisplayChunks = repairListChunkBoundaries(displayChunks.length ? displayChunks : list);\n'
        '  const idx = chunkIndexFromList(list, frame, durFrames, timingWeights);\n'
        '  const current = list[idx] || "";\n'
        '  const displaySource = repairedDisplayChunks[idx] || current;\n',
        "CasualCaption runtime repair",
    )
    if text != original:
        backup(CAPTION)
        write(CAPTION, text)


def patch_card() -> None:
    text = CARD.read_text(encoding="utf-8")
    if "repairListChunkBoundaries" in text:
        print("[skip] CasualCard list repair already installed")
        return
    original = text
    text = replace_once(
        text,
        'import { chunkIndexFromList, getChunkWindow } from "./chunkUtil";\n',
        'import { chunkIndexFromList, getChunkWindow, repairListChunkBoundaries } from "./chunkUtil";\n',
        "CasualCard import",
    )
    text = replace_once(
        text,
        '  const frame = useCurrentFrame();\n'
        '  const chunkIdx = chunkIndexFromList(data.caption_chunks, frame, durFrames, data.tts_chunk_weights);\n'
        '  const chunkWindow = getChunkWindow(data.caption_chunks, chunkIdx, durFrames, data.tts_chunk_weights);\n',
        '  const frame = useCurrentFrame();\n'
        '  const captionChunks = repairListChunkBoundaries(data.caption_chunks || []);\n'
        '  const displayChunks = repairListChunkBoundaries(data.display_chunks || captionChunks);\n'
        '  const chunkIdx = chunkIndexFromList(captionChunks, frame, durFrames, data.tts_chunk_weights);\n'
        '  const chunkWindow = getChunkWindow(captionChunks, chunkIdx, durFrames, data.tts_chunk_weights);\n',
        "CasualCard runtime repair",
    )
    text = replace_once(
        text,
        '        chunks={data.caption_chunks}\n'
        '        displayChunks={data.display_chunks}\n',
        '        chunks={captionChunks}\n'
        '        displayChunks={displayChunks}\n',
        "CasualCard repaired caption props",
    )
    if text != original:
        backup(CARD)
        write(CARD, text)


def patch_validator() -> None:
    text = VALIDATOR.read_text(encoding="utf-8")
    if "def validate_list_caption_layout" in text:
        print("[skip] Korean validator list guard already installed")
        return
    original = text
    text = replace_once(
        text,
        "import json\n",
        "import json\nimport re\n",
        "validator re import",
    )
    anchor = '\n\ndef main() -> int:\n'
    text = replace_once(text, anchor, PY_VALIDATOR_HELPER + anchor, "validator helper")
    text = replace_once(
        text,
        '    enhancer = load_enhancer()\n'
        '    try:\n'
        '        enhancer.validate_korean_contract(data)\n',
        '    enhancer = load_enhancer()\n'
        '    try:\n'
        '        validate_list_caption_layout(data)\n'
        '        enhancer.validate_korean_contract(data)\n',
        "validator call",
    )
    if text != original:
        backup(VALIDATOR)
        write(VALIDATOR, text)
        py_compile.compile(str(VALIDATOR), doraise=True)


def append_baseline() -> None:
    if not BASELINE.exists():
        return
    text = BASELINE.read_text(encoding="utf-8", errors="replace")
    if "## List-caption layout guard" in text:
        print("[skip] baseline already documents list-caption guard")
        return
    backup(BASELINE)
    write(BASELINE, text.rstrip() + "\n" + BASELINE_APPEND.strip() + "\n")


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - List Caption Layout Guard")
    print("============================================================")
    for path in (CHUNK_UTIL, CAPTION, CARD, VALIDATOR):
        if not path.exists():
            raise RuntimeError(f"required file missing: {path}")
    patch_chunk_util()
    patch_caption()
    patch_card()
    patch_validator()
    append_baseline()
    print("[OK] Global list-caption layout guard installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
