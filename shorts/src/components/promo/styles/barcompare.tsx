import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { FONT, COL, clamp, easeOut, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Bar: React.FC<{ label: string; w: number; col: string; fg: string }> = ({ label, w, col, fg }) => (
  <div style={{ width: "100%", marginBottom: 44 }}>
    <div style={{ fontSize: 50, fontWeight: 800, color: fg, marginBottom: 14, wordBreak: "keep-all" }}>{label}</div>
    <div style={{ height: 96, background: "rgba(255,255,255,0.12)", borderRadius: 16 }}>
      <div style={{ width: `${w}%`, height: "100%", background: col, borderRadius: 16 }} />
    </div>
  </div>
);

// 두 막대 라벨을 '대본(caption_chunks)'에서 도출. (구: "조회한 가격"/"개통할 때 가격" 하드코딩 → 제거)
// 규칙: 청크를 이어 "vs"가 있으면 좌/우로 분리, 없으면 앞 두 청크를 두 막대로, 나머지는 하단 캡션.
const deriveLabels = (c: string[]): { L: string; R: string; caption: string } => {
  const joined = c.join(" ");
  const parts = joined.split(/\s*vs\.?\s*/i);
  if (parts.length >= 2) {
    return { L: parts[0].trim(), R: parts.slice(1).join(" vs ").trim(), caption: "" };
  }
  return { L: c[0] ?? "", R: c[1] ?? "", caption: c.slice(2).join(" ").trim() };
};

const Scene: React.FC<SceneProps> = ({ data, durFrames, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  const { L, R, caption } = deriveLabels(c);
  const w1 = easeOut(clamp(frame / (durFrames * 0.55))) * 100;
  const w2 = easeOut(clamp((frame - 12) / (durFrames * 0.55))) * 100;
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", padding: "0 110px" }}>
      <Bar label={L} w={w1} col={COL.DIM} fg={variant.fg} />
      <Bar label={R} w={w2} col={variant.accent} fg={variant.fg} />
      {caption ? (
        <div style={{ fontSize: 66, fontWeight: 900, color: variant.fg, marginTop: 18, textAlign: "center", opacity: clamp((frame - 32) / 12), wordBreak: "keep-all" }}>{caption}</div>
      ) : null}
    </AbsoluteFill>
  );
};
export const barcompare: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
