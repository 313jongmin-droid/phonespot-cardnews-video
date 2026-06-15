import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { FONT, COL, clamp, easeOut, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Bar: React.FC<{ label: string; w: number; col: string; fg: string }> = ({ label, w, col, fg }) => (
  <div style={{ width: "100%", marginBottom: 44 }}>
    <div style={{ fontSize: 46, fontWeight: 700, color: fg, marginBottom: 14 }}>{label}</div>
    <div style={{ height: 96, background: "rgba(255,255,255,0.12)", borderRadius: 16 }}>
      <div style={{ width: `${w}%`, height: "100%", background: col, borderRadius: 16 }} />
    </div>
  </div>
);

const Scene: React.FC<SceneProps> = ({ data, durFrames, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  const w1 = easeOut(clamp(frame / (durFrames * 0.55))) * 100;
  const w2 = easeOut(clamp((frame - 12) / (durFrames * 0.55))) * 100;
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", padding: "0 110px" }}>
      <Bar label="조회한 가격" w={w1} col={COL.DIM} fg={variant.fg} />
      <Bar label="개통할 때 가격" w={w2} col={variant.accent} fg={variant.fg} />
      <div style={{ fontSize: 66, fontWeight: 900, color: variant.fg, marginTop: 18, textAlign: "center", opacity: clamp((frame - 32) / 12), wordBreak: "keep-all" }}>{c[c.length - 1]}</div>
    </AbsoluteFill>
  );
};
export const barcompare: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
