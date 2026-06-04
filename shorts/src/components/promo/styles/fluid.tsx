import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { FONT, COL, clamp, chunksOf, beatAt, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Scene: React.FC<SceneProps> = ({ data, durFrames, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  const { idx, lf, beatDur } = beatAt(frame, durFrames, c.length);
  const p = clamp(lf / beatDur);
  const w = Math.round(interpolate(p, [0, 1], [180, 900]));
  const ls = interpolate(p, [0, 0.5, 1], [12, -2, 3]);
  const last = idx === c.length - 1;
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", alignItems: "center", padding: 90 }}>
      <div style={{ fontSize: 132, color: last ? variant.accent : variant.fg, fontWeight: w as any, fontVariationSettings: `'wght' ${w}`, letterSpacing: ls, textAlign: "center", lineHeight: 1.1, opacity: clamp(lf / 4), wordBreak: "keep-all" }}>{c[idx]}</div>
    </AbsoluteFill>
  );
};
export const fluid: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
