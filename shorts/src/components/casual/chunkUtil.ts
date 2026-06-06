const countChars = (value: string) => value.replace(/\s/g, "").length;

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



// CODEX_CAPTION_COMPILER_V2
// Keep the 72px type contract. Use the browser's real Pretendard metrics to
// select line breaks instead of shrinking the type when a caption is long.
const CAPTION_FONT_SIZE = 72;
const CAPTION_FONT_WEIGHT = 900;
const CAPTION_MAX_LINE_PIXELS = 920;
let captionMeasureContext: CanvasRenderingContext2D | null | undefined;

const getCaptionMeasureContext = () => {
  if (captionMeasureContext !== undefined) {
    return captionMeasureContext;
  }
  if (typeof document === "undefined") {
    captionMeasureContext = null;
    return captionMeasureContext;
  }
  const canvas = document.createElement("canvas");
  captionMeasureContext = canvas.getContext("2d");
  return captionMeasureContext;
};

const measureCaptionPixels = (value: string) => {
  const context = getCaptionMeasureContext();
  if (!context) {
    return estimateDisplayUnits(value) * CAPTION_FONT_SIZE;
  }
  context.font = `${CAPTION_FONT_WEIGHT} ${CAPTION_FONT_SIZE}px Pretendard, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif`;
  return context.measureText(value).width;
};

const AWKWARD_LINE_END_RE = /(?:\uc2dc\ud589\ub839|\uc2dc\ud589\uaddc\uce59|\ubc95\ub960|\ubc95|\uc81c?\d+\uc870(?:\uc758\d+)?|\d+(?:[,.]\d+)?(?:\ub9cc|\uc5b5|\uc870)?)$/;


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


const FPS = 30;
// Per-caption readability floor (~0.5s). Kept deliberately small so caption
// timing stays proportional to the actual speech weights. See:
//   MAINTENANCE/CODEX_SYNC_AND_VISUAL_MATCH_FIX_GUIDE.md
// Do NOT raise this toward the average chunk length again - the old 1.1s floor
// flattened speech timing and caused the TTS/caption desync.
const CAPTION_MIN_READABLE_FRAMES = Math.round(FPS * 0.5);
const MIN_VISUAL_FRAMES = Math.round(FPS * 2.2);
const TARGET_VISUAL_FRAMES = Math.round(FPS * 3.2);
const MAX_VISUAL_FRAMES = Math.round(FPS * 4.2);

const PROTECTED_PATTERNS = [
  /(?:\uc2dc\ud589\ub839|\uc2dc\ud589\uaddc\uce59|\ubc95\ub960|\ubc95|\uace0\uc2dc|\uc870\ub840|\uaddc\uce59)\s+\uc81c?\s*\d+\s*\uc870(?:\uc758\s*\d+)?(?:[\uc740\ub294\uc774\uac00\uc744\ub97c\uc5d0\ub3c4]|\uc73c\ub85c|\uc5d0\uc11c)?/g,
  /\d+\s*\ub9cc\s*\uc6d0(?:\ub300(?:[\uc740\ub294\uc774\uac00\uc744\ub97c\uc5d0\ub3c4]|\uc73c\ub85c|\uc5d0\uc11c|\ubd80\ud130|\uae4c\uc9c0)?|\uc5d0\uc11c|\ubd80\ud130|\uae4c\uc9c0)?/g,
  /\d+(?:[,.]\d+)?\s*(?:\uc6d0|\ub9cc\uc6d0|\uc5b5\uc6d0|\uc870\uc6d0|\ud37c\uc13c\ud2b8|%|\uc720\ub85c|\ub2ec\ub7ec|\uac1c|\uba85|\uac1c\uc6d4)(?:[\uc740\ub294\uc774\uac00\uc744\ub97c\uc5d0\ub3c4]|\uc73c\ub85c|\uc5d0\uc11c|\uae4c\uc9c0)?/g,
  /(?:\uc544\uc774\ud3f0|\uac24\ub7ed\uc2dc|\ud53d\uc140|\uc544\uc774\ud328\ub4dc|\uac24\ub7ed\uc2dc\ud0ed)\s*[A-Za-z0-9+.-]+(?:\s*(?:\ud504\ub85c|\ud50c\ub7ec\uc2a4|\uc6b8\ud2b8\ub77c|\uc5d0\uc5b4|FE|\ud3f4\ub4dc|\ud50c\ub9bd))?/gi,
  /WWDC\s*\d+/gi,
  /iOS\s*\d+(?:\.\d+)*/gi,
  /One\s*UI\s*\d+(?:\.\d+)*/gi,
  /Android\s*\d+(?:\.\d+)*/gi,
  /Gemini/gi,
  /Siri/gi,
  /NFC/gi,
  /RCS/gi,
  /(?:\uAC24\uB7ED\uC2DC\s*)?S\s*\d{2}/gi,
  /Z\s*\uD3F4\uB4DC\s*\d+/g,
  /Z\s*\uD50C\uB9BD\s*\d+/g,
  /\d+\s*\uC6D4\s*\d+\s*\uC77C/g,
  /\d+\s*\/\s*\d+/g,
  /\d+(?:[,.]?\d+)*\s*(?:\uB9CC\s*)?\uC6D0/g,
  /\d+(?:[,.]?\d+)*\s*(?:\uC720\uB85C|\uB2EC\uB7EC|\uAC1C|\uBA85|%)\b/g,
];

const BREAK_AFTER_ENDINGS = [
  "\uBA70",
  "\uACE0",
  "\uC9C0\uB9CC",
  "\uC778\uB370",
  "\uC73C\uB85C",
  "\uB85C",
  "\uC5D0\uC11C",
  "\uAE4C\uC9C0",
  "\uBD80\uD130",
  "\uD558\uBA74",
  "\uD558\uBA70",
  "\uB418\uACE0",
  "\uB418\uB294",
  "\uC804\uB9DD",
  "\uBCF4\uB3C4",
  "\uBD84\uC11D",
  "\uC608\uC815",
  "\uAC00\uB2A5\uC131",
  "\uB54C\uBB38",
];

const BAD_LINE_STARTS = new Set([
  "\uC740",
  "\uB294",
  "\uC774",
  "\uAC00",
  "\uC744",
  "\uB97C",
  "\uC5D0",
  "\uC758",
  "\uB3C4",
  "\uB9CC",
  "\uACFC",
  "\uC640",
  "\uB85C",
  "\uC73C\uB85C",
  "\uBD80\uD130",
  "\uAE4C\uC9C0",
  "\uC5D0\uC11C",
  "\uB77C\uACE0",
  "\uB77C\uB294",
  "\uD558\uBA70",
  "\uD558\uACE0",
  "\uADF8\uB9AC\uACE0",
  "\uB610",
  "\uBC0F",
]);

const protectTokens = (text: string) => {
  const protectedTokens: string[] = [];
  let output = text.replace(/(^|\s)(\d{1,2}[\)\.])\s+([^\s]+)/g, (_match, prefix, marker, word) => {
    const key = `__PS${protectedTokens.length}__`;
    protectedTokens.push(`${marker}\u00A0${word}`);
    return `${prefix}${key}`;
  });

  for (const pattern of PROTECTED_PATTERNS) {
    output = output.replace(pattern, (match) => {
      const key = `__PS${protectedTokens.length}__`;
      protectedTokens.push(match.replace(/\s+/g, "\u00A0"));
      return key;
    });
  }

  return {
    text: output,
    restore: (value: string) =>
      value.replace(/__PS(\d+)__/g, (_, idx) => protectedTokens[Number(idx)] || ""),
  };
};

const shouldBreakAfter = (word: string) =>
  BREAK_AFTER_ENDINGS.some((ending) => word.endsWith(ending));

const isBadLineStart = (word: string) => BAD_LINE_STARTS.has(word);

const mergeBadStarts = (chunks: string[]) => {
  const merged: string[] = [];

  for (const chunk of chunks) {
    const first = chunk.split(/\s+/)[0] || "";
    if (merged.length && isBadLineStart(first)) {
      merged[merged.length - 1] = `${merged[merged.length - 1]} ${chunk}`.trim();
    } else {
      merged.push(chunk);
    }
  }

  return merged;
};

export function splitChunks(text: string, maxChars = 14): string[] {
  const protectedText = protectTokens(text.replace(/\n/g, " ").trim());
  const words = protectedText.text.split(/\s+/).filter(Boolean);
  const chunks: string[] = [];
  let cur = "";

  for (const word of words) {
    const merged = cur ? `${cur} ${word}` : word;
    const mergedLen = countChars(merged);
    const softBreak =
      cur && countChars(cur) >= Math.floor(maxChars * 0.72) && shouldBreakAfter(cur);

    if ((mergedLen > maxChars || softBreak) && cur) {
      chunks.push(cur);
      cur = word;
    } else {
      cur = merged;
    }
  }

  if (cur) {
    chunks.push(cur);
  }

  return mergeBadStarts(chunks).map((chunk) => protectedText.restore(chunk));
}

const moveBadLineStarts = (lines: string[]) => {
  const out = lines.filter(Boolean);
  for (let i = 1; i < out.length; i++) {
    const words = out[i].split(/\s+/).filter(Boolean);
    const first = words[0] || "";
    if (isBadLineStart(first)) {
      out[i - 1] = `${out[i - 1]} ${first}`.trim();
      out[i] = words.slice(1).join(" ");
    }
  }
  return out.filter(Boolean);
};

const scoreLines = (lines: string[]) => {
  const widths = lines.map(measureCaptionPixels);
  const overflow = widths.reduce((sum, width) => sum + Math.max(0, width - CAPTION_MAX_LINE_PIXELS), 0);
  const spread = Math.max(...widths) - Math.min(...widths);
  const badStartPenalty = lines.slice(1).reduce((sum, line) => {
    const first = line.split(/\s+/)[0] || "";
    return sum + (isBadLineStart(first) ? 400 : 0);
  }, 0);
  const awkwardEndPenalty = lines.slice(0, -1).reduce((sum, line) => {
    const last = line.split(/\s+/).filter(Boolean).pop() || "";
    return sum + (AWKWARD_LINE_END_RE.test(last) ? 260 : 0);
  }, 0);
  const rhythmBonus = lines.slice(0, -1).reduce((sum, line) => {
    const words = line.split(/\s+/).filter(Boolean);
    const last = words.length ? words[words.length - 1] : "";
    return sum + (shouldBreakAfter(last) ? -18 : 0);
  }, 0);
  return overflow * 30 + spread * 0.16 + badStartPenalty + awkwardEndPenalty + rhythmBonus + (lines.length - 1) * 28;
};


// Display-caption punctuation guard:
// - Hide sentence periods on screen for a cleaner Shorts caption style.
// - Keep decimal/version separators such as `26.6` and `1.5`.
// - TTS and authored narration are not modified.
export const stripDisplaySentencePeriods = (value: string) =>
  value.replace(/\.(?=(?:["'”’)]*)?(?:\s|$))/g, "");

export function formatCaptionLines(text: string, _maxLineChars = 18, maxLines = 3): string {
  const clean = stripDisplaySentencePeriods(text).replace(/\n/g, " ").trim();
  if (!clean) {
    return clean;
  }

  const protectedText = protectTokens(clean);
  const words = protectedText.text.split(/\s+/).filter(Boolean);
  if (words.length <= 1) {
    return protectedText.restore(clean);
  }

  let best = { lines: [protectedText.restore(protectedText.text)], score: Number.POSITIVE_INFINITY };

  const tryBreaks = (breaks: number[]) => {
    const lines: string[] = [];
    let start = 0;
    for (const br of breaks) {
      lines.push(words.slice(start, br).join(" "));
      start = br;
    }
    lines.push(words.slice(start).join(" "));
    const restored = lines.map((line) => protectedText.restore(line));
    const fixed = moveBadLineStarts(restored);
    const score = scoreLines(fixed);
    if (score < best.score) {
      best = { lines: fixed, score };
    }
  };

  tryBreaks([]);
  if (maxLines >= 2) {
    for (let i = 1; i < words.length; i++) {
      tryBreaks([i]);
    }
  }
  if (maxLines >= 3) {
    for (let i = 1; i < words.length - 1; i++) {
      for (let j = i + 1; j < words.length; j++) {
        tryBreaks([i, j]);
      }
    }
  }

  return best.lines.join("\n");
}

export function getChunkWindows(chunks: string[], durFrames: number, timingWeights?: number[]) {
  const clean = chunks && chunks.length ? chunks : [""];
  const hasTimingWeights =
    timingWeights?.length === clean.length && timingWeights.every((value) => Number.isFinite(value) && value > 0);
  const weights = hasTimingWeights
    ? timingWeights!.map((value) => Math.max(1, value))
    : clean.map((chunk) => Math.max(1, countChars(chunk)));
  const totalWeight = weights.reduce((sum, weight) => sum + weight, 0) || 1;
  // Floor must never exceed half the average chunk length, so at least ~50% of
  // the section timeline always follows the real speech weights (prevents the
  // old "equal-spacing" desync). See MAINTENANCE/CODEX_SYNC_AND_VISUAL_MATCH_FIX_GUIDE.md
  const avgFrames = durFrames / clean.length;
  const minFrames = Math.max(
    4,
    Math.min(CAPTION_MIN_READABLE_FRAMES, Math.floor(avgFrames * 0.5))
  );
  const spareFrames = Math.max(0, durFrames - minFrames * clean.length);

  let cursor = 0;
  return clean.map((_, idx) => {
    const isLast = idx === clean.length - 1;
    const variableFrames = isLast
      ? Math.max(0, durFrames - cursor - minFrames)
      : Math.round((weights[idx] / totalWeight) * spareFrames);
    const duration = Math.max(1, minFrames + variableFrames);
    const start = cursor;
    const end = isLast ? durFrames : Math.min(durFrames, start + duration);
    cursor = end;
    return {
      start,
      end,
      duration: Math.max(1, end - start),
    };
  });
}

export function getChunkWindow(chunks: string[], idx: number, durFrames: number, timingWeights?: number[]) {
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
}

export function chunkInfo(text: string, frame: number, durFrames: number, maxChars = 14) {
  const chunks = splitChunks(text, maxChars);
  const idx = chunkIndexFromList(chunks, frame, durFrames);
  return { chunks, idx, count: chunks.length };
}

export function chunkIndexFromList(chunks: string[], frame: number, durFrames: number, timingWeights?: number[]) {
  const windows = getChunkWindows(chunks, durFrames, timingWeights);
  let idx = 0;
  for (let i = 0; i < windows.length; i++) {
    if (frame >= windows[i].start) {
      idx = i;
    }
  }
  return Math.min(idx, windows.length - 1);
}
