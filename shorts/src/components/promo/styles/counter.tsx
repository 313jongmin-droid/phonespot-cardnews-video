import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { FONT, COL, clamp, easeOut, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Scene: React.FC<SceneProps> = ({ data, durFrames, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  const m = c.join(" ").match(/\d[\d,]*/);
  const target = m ? parseInt(m[0].replace(/,/g, ""), 10) : 100;
  const p = clamp(frame / (durFrames * 0.7));
  const val = Math.round(target * easeOut(p));
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <div style={{ fontSize: 240, fontWeight: 900, color: variant.accent, letterSpacing: -4, lineHeight: 1 }}>{val.toLocaleString()}</div>
      <div style={{ fontSize: 70, fontWeight: 900, color: variant.fg, marginTop: 16, textAlign: "center", wordBreak: "keep-all" }}>{c[c.length - 1]}</div>
    </AbsoluteFill>
  );
};
export const counter: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
