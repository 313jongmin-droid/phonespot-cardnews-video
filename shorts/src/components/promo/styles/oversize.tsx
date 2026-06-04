import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { FONT, COL, clamp, easeOut, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Scene: React.FC<SceneProps> = ({ data, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  const kicker = c.length > 1 ? c[0] : "";
  const big = c[c.length - 1];
  const a = clamp(frame / 6);
  const s = 0.72 + 0.28 * easeOut(frame / 8);
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", alignItems: "center", padding: 70 }}>
      {kicker ? <div style={{ fontSize: 56, fontWeight: 700, color: variant.accent, opacity: a, marginBottom: 26 }}>{kicker}</div> : null}
      <div style={{ transform: `scale(${s})`, opacity: a, fontSize: 150, fontWeight: 900, color: variant.fg, textAlign: "center", lineHeight: 1.02, letterSpacing: -2, wordBreak: "keep-all" }}>{big}</div>
    </AbsoluteFill>
  );
};
export const oversize: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
