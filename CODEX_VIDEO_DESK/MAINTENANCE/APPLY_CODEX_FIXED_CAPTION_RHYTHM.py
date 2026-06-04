# -*- coding: utf-8 -*-
"""Install fixed-size captions and a slower visual rhythm for Codex Remotion."""
from __future__ import annotations

import os
import py_compile
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


DEFAULT_ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
ROOT = Path(os.environ.get("PHONESPOT_ROOT", str(DEFAULT_ROOT)))
SHORTS = ROOT / "shorts"
CASUAL_CAPTION = SHORTS / "src" / "components" / "casual" / "CasualCaption.tsx"
CHUNK_UTIL = SHORTS / "src" / "components" / "casual" / "chunkUtil.ts"
CASUAL_CARD = SHORTS / "src" / "components" / "casual" / "CasualCard.tsx"
LOCKSTEP = SHORTS / "scripts" / "codex_caption_lockstep.py"
GENERATE_TTS = SHORTS / "scripts" / "generate_tts.py"
VERIFY_TTS = SHORTS / "scripts" / "verify_tts_timing.py"
BASELINE = SHORTS / "codex" / "CODEX_BASELINE.md"
MEMORY = SHORTS / "codex" / "CODEX_MEMORY.md"
PATCH_LOG = SHORTS / "codex" / "codex_patch_log.md"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKED_UP: set[Path] = set()


FONT_OLD = '''const getFontSize = (text: string) => {
  const lines = text.split("\\n").length;
  const len = text.replace(/\\s/g, "").length;
  if (lines >= 3) {
    if (len <= 33) return 70;
    if (len <= 42) return 64;
    return 58;
  }
  if (len <= 13) return 86;
  if (len <= 20) return 80;
  if (len <= 28) return 72;
  if (len <= 36) return 64;
  return 58;
};'''
FONT_NEW = '''// Stable typography contract: split long captions instead of shrinking the font.
const CAPTION_FONT_SIZE = 72;'''

FONT_USE_OLD = '''  const fontSize = getFontSize(displayText.replace(/\\n/g, " "));'''
FONT_USE_NEW = '''  const fontSize = CAPTION_FONT_SIZE;'''

MIN_FRAME_OLD = '''const IDEAL_MIN_CHUNK_FRAMES = FPS;'''
MIN_FRAME_NEW = '''const IDEAL_MIN_CHUNK_FRAMES = Math.round(FPS * 1.1);
const MIN_VISUAL_FRAMES = Math.round(FPS * 2.2);
const TARGET_VISUAL_FRAMES = Math.round(FPS * 3.2);
const MAX_VISUAL_FRAMES = Math.round(FPS * 4.2);'''

VISUAL_WINDOW_ANCHOR = '''export function getChunkWindow(chunks: string[], idx: number, durFrames: number, timingWeights?: number[]) {
  const windows = getChunkWindows(chunks, durFrames, timingWeights);
  return windows[Math.min(Math.max(idx, 0), windows.length - 1)];
}'''

VISUAL_WINDOW_INSERT = '''export function getChunkWindow(chunks: string[], idx: number, durFrames: number, timingWeights?: number[]) {
  const windows = getChunkWindows(chunks, durFrames, timingWeights);
  return windows[Math.min(Math.max(idx, 0), windows.length - 1)];
}

// Captions follow TTS boundaries. Visuals use a calmer, independent timeline.
// This prevents source images from flashing past when a narration sentence is
// split into multiple readable Korean caption chunks.
export function getVisualWindow(chunks: string[], frame: number, durFrames: number, timingWeights?: number[]) {
  const windows = getChunkWindows(chunks, durFrames, timingWeights);
  if (!windows.length) {
    return { start: 0, end: Math.max(1, durFrames), duration: Math.max(1, durFrames), visualIndex: 0 };
  }

  const bands: Array<{ start: number; end: number; duration: number; visualIndex: number }> = [];
  let startChunk = 0;

  const pushBand = (endChunk: number) => {
    const start = windows[startChunk].start;
    const end = windows[endChunk].end;
    bands.push({ start, end, duration: Math.max(1, end - start), visualIndex: startChunk });
    startChunk = endChunk + 1;
  };

  for (let idx = 0; idx < windows.length; idx++) {
    const duration = windows[idx].end - windows[startChunk].start;
    const isLast = idx === windows.length - 1;
    const nextDuration = isLast ? duration : windows[idx + 1].end - windows[startChunk].start;
    if (isLast || (duration >= MIN_VISUAL_FRAMES && nextDuration > TARGET_VISUAL_FRAMES)) {
      pushBand(idx);
    }
  }

  if (bands.length >= 2) {
    const last = bands[bands.length - 1];
    const previous = bands[bands.length - 2];
    if (last.duration < MIN_VISUAL_FRAMES && previous.duration + last.duration <= Math.round(MAX_VISUAL_FRAMES * 1.25)) {
      previous.end = last.end;
      previous.duration = previous.end - previous.start;
      bands.pop();
    }
  }

  return bands.find((band) => frame >= band.start && frame < band.end) || bands[bands.length - 1];
}'''

CARD_IMPORT_OLD = '''import { chunkIndexFromList, getChunkWindow, repairListChunkBoundaries } from "./chunkUtil";'''
CARD_IMPORT_NEW = '''import { chunkIndexFromList, getChunkWindow, getVisualWindow, repairListChunkBoundaries } from "./chunkUtil";'''

CARD_WINDOW_OLD = '''  const chunkWindow = getChunkWindow(captionChunks, chunkIdx, durFrames, data.tts_chunk_weights);
  const chunkFrame = Math.max(0, frame - chunkWindow.start);
  const visuals = data.chunk_visuals || [];
  const visualVariant = chunkIdx + audioKey.split("").reduce((sum, ch) => sum + ch.charCodeAt(0), 0);

  const cv: ChunkVisual =
    visuals[chunkIdx] ||'''

CARD_WINDOW_NEW = '''  const chunkWindow = getChunkWindow(captionChunks, chunkIdx, durFrames, data.tts_chunk_weights);
  const visualWindow =
    type === "cta"
      ? { ...chunkWindow, visualIndex: chunkIdx }
      : getVisualWindow(captionChunks, frame, durFrames, data.tts_chunk_weights);
  const visualChunkFrame = Math.max(0, frame - visualWindow.start);
  const visualIdx = visualWindow.visualIndex;
  const visuals = data.chunk_visuals || [];
  const visualVariant = visualIdx + audioKey.split("").reduce((sum, ch) => sum + ch.charCodeAt(0), 0);

  const cv: ChunkVisual =
    visuals[visualIdx] ||'''

CARD_IMAGE_OLD = '''            chunkFrame={chunkFrame}
            chunkDurFrames={chunkWindow.duration}'''
CARD_IMAGE_NEW = '''            chunkFrame={visualChunkFrame}
            chunkDurFrames={visualWindow.duration}'''

CARD_INTRO_OLD = '''    ? interpolate(chunkFrame, [0, 5], [0.86, 1], {'''
CARD_INTRO_NEW = '''    ? interpolate(visualChunkFrame, [0, 5], [0.86, 1], {'''

CARD_SCALE_OLD = '''    ? interpolate(chunkFrame, [0, 5], [0.985, 1], {'''
CARD_SCALE_NEW = '''    ? interpolate(visualChunkFrame, [0, 5], [0.985, 1], {'''

LOCKSTEP_OLD = '''MIN_UNITS = 9
TARGET_UNITS = 19
MAX_UNITS = 27
ABSOLUTE_MAX_UNITS = 34'''
LOCKSTEP_NEW = '''MIN_UNITS = 9
TARGET_UNITS = 17
MAX_UNITS = 24
ABSOLUTE_MAX_UNITS = 30'''

TTS_MIN_OLD = '''MIN_CHUNK_MS = int(os.getenv("PHONESPOT_TTS_MIN_CHUNK_MS", "900"))'''
TTS_MIN_NEW = '''MIN_CHUNK_MS = int(os.getenv("PHONESPOT_TTS_MIN_CHUNK_MS", "1100"))'''

VERIFY_OLD = '''        for idx, value in enumerate(weights, 1):
            if float(value) < 600:
                warnings.append(f"{key}.chunk[{idx}]: short visible window {float(value):.0f}ms")'''
VERIFY_NEW = '''        for idx, value in enumerate(weights, 1):
            visible_ms = float(value)
            if visible_ms < 650:
                errors.append(f"{key}.chunk[{idx}]: unusably short visible window {visible_ms:.0f}ms")
            elif visible_ms < 1100:
                warnings.append(f"{key}.chunk[{idx}]: short visible window {visible_ms:.0f}ms")'''


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def backup(path: Path, label: str) -> None:
    resolved = path.resolve()
    if not path.exists() or resolved in BACKED_UP:
        return
    target = path.with_name(f"{path.name}.bak_{label}_{STAMP}")
    shutil.copy2(path, target)
    BACKED_UP.add(resolved)
    print(f"[backup] {target}")


def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"[write] {path}")


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    if not path.exists():
        raise RuntimeError(f"{label} file missing: {path}")
    text = read(path)
    if new in text:
        print(f"[skip] already current: {path}")
        return
    if old not in text:
        raise RuntimeError(f"{label} patch anchor missing: {path}")
    backup(path, "fixed_caption_rhythm")
    write(path, text.replace(old, new, 1))


def append_once(path: Path, marker: str, body: str) -> None:
    text = read(path)
    if marker in text:
        print(f"[skip] already documented: {path.name}")
        return
    write(path, text.rstrip() + "\n\n" + body.strip() + "\n")


def main() -> int:
    print("=" * 60)
    print(" PhoneSpot Codex - Fixed Caption Font and Visual Rhythm")
    print("=" * 60)
    replace_once(CASUAL_CAPTION, FONT_OLD, FONT_NEW, "caption font")
    replace_once(CASUAL_CAPTION, FONT_USE_OLD, FONT_USE_NEW, "caption font usage")
    replace_once(CHUNK_UTIL, MIN_FRAME_OLD, MIN_FRAME_NEW, "caption minimum frame")
    replace_once(CHUNK_UTIL, VISUAL_WINDOW_ANCHOR, VISUAL_WINDOW_INSERT, "visual window")
    replace_once(CASUAL_CARD, CARD_IMPORT_OLD, CARD_IMPORT_NEW, "card import")
    replace_once(CASUAL_CARD, CARD_WINDOW_OLD, CARD_WINDOW_NEW, "card visual window")
    replace_once(CASUAL_CARD, CARD_IMAGE_OLD, CARD_IMAGE_NEW, "card image motion")
    replace_once(CASUAL_CARD, CARD_INTRO_OLD, CARD_INTRO_NEW, "card visual opacity")
    replace_once(CASUAL_CARD, CARD_SCALE_OLD, CARD_SCALE_NEW, "card visual scale")
    replace_once(LOCKSTEP, LOCKSTEP_OLD, LOCKSTEP_NEW, "Korean caption splitter")
    replace_once(GENERATE_TTS, TTS_MIN_OLD, TTS_MIN_NEW, "TTS minimum timing")
    replace_once(VERIFY_TTS, VERIFY_OLD, VERIFY_NEW, "TTS timing verifier")
    append_once(
        BASELINE,
        "## Fixed caption font and independent visual rhythm",
        """## Fixed caption font and independent visual rhythm
- Casual screen captions render at one stable 72px font size.
- Long narration is split at Korean sentence, comma, connective-ending, or safe word boundaries instead of shrinking caption text.
- Caption windows follow edge-tts WordBoundary timing. A sub-650ms caption window blocks rendering; sub-1100ms windows are reported.
- Visual windows are independent from caption windows and generally stay visible for about 2.2 to 4.2 seconds.
- CTA visuals, illustrations, logos, mascots, and infographics remain static. Existing CTA, source-image-once, Korean, and TTS lockstep contracts remain active.""",
    )
    append_once(
        MEMORY,
        "## 37. Fixed caption font and independent visual rhythm",
        """## 37. Fixed caption font and independent visual rhythm
- Do not shrink Casual screen-caption text to fit a long chunk. Keep 72px typography stable.
- Split long narration conservatively while preserving lossless TTS-caption lockstep and Korean grammar boundaries.
- Caption changes and visual changes use separate timelines. Source images should not flash past because a sentence was split for readability.
- CTA, illustrations, logos, mascots, and infographics stay static.""",
    )
    append_once(
        PATCH_LOG,
        "## 2026-06-02 - Fixed caption font and independent visual rhythm",
        """## 2026-06-02 - Fixed caption font and independent visual rhythm
- Replaced variable Casual caption sizing with a stable 72px size.
- Tightened Korean TTS-caption chunk targets without changing narration content.
- Added TTS WordBoundary timing warnings and a fail-closed lower bound.
- Decoupled source-image dwell time from faster caption changes.""",
    )
    for path in (LOCKSTEP, GENERATE_TTS, VERIFY_TTS):
        py_compile.compile(str(path), doraise=True)
    if (SHORTS / "tsconfig.json").exists():
        subprocess.run(["cmd", "/c", "npx tsc --noEmit"], cwd=SHORTS, check=True)
    print("[OK] Fixed caption font and visual rhythm installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
