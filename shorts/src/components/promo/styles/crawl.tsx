import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { FONT, COL, clamp, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Scene: React.FC<SceneProps> = ({ data, durFrames, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  const y = interpolate(clamp(frame / durFrames), [0, 1], [780, -c.length * 130 + 200]);
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, overflow: "hidden" }}>
      <div style={{ position: "absolute", left: 0, right: 0, transform: `translateY(${y}px)`, display: "flex", flexDirection: "column", gap: 44, alignItems: "center" }}>
        {c.map((ln, i) => (
          <div key={i} style={{ fontSize: i === c.length - 1 ? 110 : 90, fontWeight: 900, color: i === c.length - 1 ? variant.accent : variant.fg, textAlign: "center", letterSpacing: -1 }}>{ln}</div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
export const crawl: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
