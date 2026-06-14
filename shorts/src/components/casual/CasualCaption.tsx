import React from "react";
import { useCurrentFrame } from "remotion";
import { chunkIndexFromList, formatCaptionLines, repairListChunkBoundaries } from "./chunkUtil";

interface Props {
  chunks: string[];
  displayChunks?: string[];
  emphasisWords?: string[];
  timingWeights?: number[];
  durFrames: number;
}

const AUTO_EMPHASIS_PATTERNS: RegExp[] = [
  /\d+(?:[,.]?\d+)*\s*(?:\uB9CC\s*)?\uC6D0/g,
  /\d+(?:[,.]?\d+)*\s*\uC5B5/g,
  /\d+(?:[,.]?\d+)*\s*\uC870\s*\uC6D0/g,
  /\d+(?:[,.]?\d+)*\s*\uC870\s*\uB2EC\uB7EC/g,
  /\d+(?:[,.]?\d+)*\s*\uC720\uB85C/g,
  /\d+(?:[,.]?\d+)*\s*\uB2EC\uB7EC/g,
  /\$\s*\d+(?:[,.]?\d+)*/g,
  /\u20A9\s*\d+(?:[,.]?\d+)*/g,
  /\d+(?:\.\d+)?\s*%/g,
  /\d+(?:[,.]?\d+)*\s*\uAC1C/g,
  /\d+(?:[,.]?\d+)*\s*\uBA85/g,
  /\d+\s*\uC6D4\s*\d+\s*\uC77C/g,
  /\d+\s*\uB144/g,
  /\d+(?:\.\d+)*\s*(?:GB|TB|MB|kbps|Mbps|Gbps|W)/gi,
  /iOS\s*\d+(?:\.\d+)*/gi,
  /Android\s*\d+/gi,
  /S\s*\d{2}/g,
  /Z\s*\uD3F4\uB4DC\s*\d+/g,
  /Z\s*\uD50C\uB9BD\s*\d+/g,
  /WWDC\s*\d+/g,
  /Gemini/gi,
  /Siri/gi,
  /NFC/gi,
];

const normalize = (value: string) =>
  value.replace(/[()\[\]\u00B7,.\s]/g, "").toLowerCase();

const addRange = (ranges: Array<[number, number]>, start: number, end: number) => {
  if (start >= 0 && end > start) {
    ranges.push([start, end]);
  }
};

function matchLoose(text: string, needle: string): [number, number] | null {
  const cleanedNeedle = normalize(needle);
  if (cleanedNeedle.length < 2) {
    return null;
  }

  let compact = "";
  const map: number[] = [];
  for (let i = 0; i < text.length; i++) {
    const normalized = normalize(text[i]);
    if (!normalized) {
      continue;
    }
    compact += normalized;
    map.push(i);
  }

  const compactIdx = compact.indexOf(cleanedNeedle);
  if (compactIdx < 0) {
    return null;
  }

  const start = map[compactIdx];
  const end = map[Math.min(map.length - 1, compactIdx + cleanedNeedle.length - 1)] + 1;
  return [start, end];
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function buildSegments(text: string, emphasisWords: string[]): { text: string; emph: boolean }[] {
  const ranges: Array<[number, number]> = [];

  // 작성자가 지정한 caption_emphasis 구절만 강조한다. 자동 숫자/단위 강조는 OFF
  // (과다·번짐의 원인). 토큰 사이 공백/줄바꿈만 허용하는 정확 매칭 → 부분 매칭·경계
  // 가로지르기 불가. 깔끔히 못 맞으면 스킵해서 색을 안 칠한다("애매하면 안 칠한다").
  for (const word of emphasisWords || []) {
    const phrase = String(word || "").trim();
    if (phrase.length < 2) continue;
    const tokens = phrase.split(/\s+/).filter(Boolean).map(escapeRegExp);
    if (!tokens.length) continue;
    const re = new RegExp(tokens.join("\\s*"), "gi");
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      addRange(ranges, m.index, m.index + m[0].length);
      if (m[0].length === 0) re.lastIndex += 1;
    }
  }

  if (!ranges.length) {
    return [{ text, emph: false }];
  }

  ranges.sort((a, b) => a[0] - b[0]);
  const merged: Array<[number, number]> = [];
  for (const range of ranges) {
    const last = merged[merged.length - 1];
    if (last && range[0] <= last[1]) {
      last[1] = Math.max(last[1], range[1]);
    } else {
      merged.push([...range]);
    }
  }

  const segments: { text: string; emph: boolean }[] = [];
  let cursor = 0;
  for (const [start, end] of merged) {
    if (start > cursor) {
      segments.push({ text: text.slice(cursor, start), emph: false });
    }
    segments.push({ text: text.slice(start, end), emph: true });
    cursor = end;
  }
  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), emph: false });
  }
  return segments;
}

// Stable typography contract: split long captions instead of shrinking the font.
const CAPTION_FONT_SIZE = 72;

export const CasualCaption: React.FC<Props> = ({
  chunks,
  displayChunks = [],
  emphasisWords = [],
  timingWeights,
  durFrames,
}) => {
  const frame = useCurrentFrame();
  const list = repairListChunkBoundaries(chunks && chunks.length ? chunks : [""]);
  const repairedDisplayChunks = repairListChunkBoundaries(displayChunks.length ? displayChunks : list);
  const idx = chunkIndexFromList(list, frame, durFrames, timingWeights);
  const current = list[idx] || "";
  const displaySource = repairedDisplayChunks[idx] || current;
  const displayText = formatCaptionLines(displaySource, 18, 3);
  const segments = buildSegments(displayText, emphasisWords);
  const fontSize = CAPTION_FONT_SIZE;

  return (
    <div
      style={{
        height: 840,
        backgroundColor: "#FFFFFF",
        padding: "128px 56px 0",
        boxSizing: "border-box",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        fontFamily:
          "'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
      }}
    >
      <div
        style={{
          fontSize,
          fontWeight: 900,
          lineHeight: 1.32,
          letterSpacing: 0,
          textAlign: "center",
          wordBreak: "keep-all",
          whiteSpace: "pre-wrap",
          overflowWrap: "normal",
          lineBreak: "strict",
          maxWidth: 960,
        }}
      >
        {segments.map((seg, i) => (
          <span
            key={i}
            style={{
              color: seg.emph ? "#F74B0B" : "#1A1A1A",
              backgroundColor: "transparent",
              borderRadius: 0,
              padding: 0,
            }}
          >
            {seg.text}
          </span>
        ))}
      </div>
    </div>
  );
};
