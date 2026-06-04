import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { FONT, COL, clamp, chunksOf, beatAt, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Scene: React.FC<SceneProps> = ({ data, durFrames, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  const { idx, lf } = beatAt(frame, durFrames, c.length);
  const last = idx === c.length - 1;
  const j = last ? Math.sin(frame * 3.1) * 7 : 0;
  const j2 = last ? Math.cos(frame * 2.3) * 7 : 0;
  const a = clamp(lf / 3);
  const txt = c[idx];
  const base: React.CSSProperties = { fontSize: 118, fontWeight: 900, textAlign: "center", lineHeight: 1.1, letterSpacing: -1, wordBreak: "keep-all" };
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", alignItems: "center", padding: 90 }}>
      <div style={{ position: "relative", opacity: a }}>
        <div style={{ ...base, position: "absolute", inset: 0, transform: `translate(${j}px,0)`, color: "#E0670F", mixBlendMode: "screen" }}>{txt}</div>
        <div style={{ ...base, position: "absolute", inset: 0, transform: `translate(${-j2}px,0)`, color: "#7FB5C2", mixBlendMode: "screen" }}>{txt}</div>
        <div style={{ ...base, position: "relative", color: variant.fg }}>{txt}</div>
      </div>
    </AbsoluteFill>
  );
};
export const glitch: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
