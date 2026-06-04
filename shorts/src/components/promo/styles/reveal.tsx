import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT, COL, clamp, chunksOf, CtaBlock, PromoStyle, SceneProps } from "./shared";

// 스타일 A: 줄 리빌 — 각 구절을 stagger로 올리며 쌓아 보여줌 (차분/또렷)
const Opening: React.FC<{ line1: string; line2: string; durFrames: number }> = ({ line1, line2 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = (d: number) => spring({ frame: frame - d, fps, config: { damping: 200 } });
  return (
    <AbsoluteFill style={{ backgroundColor: COL.INK, fontFamily: FONT, justifyContent: "center", alignItems: "center", gap: 20 }}>
      <div style={{ fontSize: 70, fontWeight: 700, color: COL.DIM, opacity: interpolate(a(0), [0, 1], [0, 1]), transform: `translateY(${interpolate(a(0), [0, 1], [40, 0])}px)` }}>{line1}</div>
      <div style={{ fontSize: 120, fontWeight: 900, color: COL.ORANGE, opacity: interpolate(a(8), [0, 1], [0, 1]), transform: `translateY(${interpolate(a(8), [0, 1], [40, 0])}px)` }}>{line2}</div>
    </AbsoluteFill>
  );
};

const Scene: React.FC<SceneProps> = ({ data, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const lines = chunksOf(data);
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", alignItems: "center", padding: 110 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 22, alignItems: "center" }}>
        {lines.map((ln, i) => {
          const s = spring({ frame: frame - 6 - i * 9, fps, config: { damping: 200 } });
          const accent = i === lines.length - 1;
          return (
            <div key={i} style={{ opacity: interpolate(s, [0, 1], [0, 1]), transform: `translateY(${interpolate(s, [0, 1], [60, 0])}px)`, fontSize: accent ? 132 : 92, fontWeight: 900, lineHeight: 1.08, color: accent ? variant.accent : variant.fg, textAlign: "center", letterSpacing: -1 }}>{ln}</div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const Outro: React.FC<{ durFrames: number }> = () => (
  <AbsoluteFill style={{ backgroundColor: COL.ORANGE, fontFamily: FONT, justifyContent: "center", alignItems: "center" }}>
    <div style={{ fontSize: 130, fontWeight: 900, color: COL.WHITE, letterSpacing: 3 }}>폰스팟</div>
  </AbsoluteFill>
);

export const reveal: PromoStyle = { Opening, Scene, Outro };
