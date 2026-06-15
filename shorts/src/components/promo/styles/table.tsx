import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT, COL, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Scene: React.FC<SceneProps> = ({ data, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", padding: "0 80px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 26 }}>
        <div style={{ flex: 1, textAlign: "center", fontSize: 50, fontWeight: 900, color: COL.DIM }}>일반 매장</div>
        <div style={{ flex: 1, textAlign: "center", fontSize: 50, fontWeight: 900, color: variant.accent }}>폰스팟</div>
      </div>
      {c.map((ln, i) => {
        const s = spring({ frame: frame - i * 12, fps, config: { damping: 200 } });
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", padding: "26px 0", borderTop: "3px solid rgba(255,255,255,0.12)", opacity: interpolate(s, [0, 1], [0, 1]) }}>
            <div style={{ flex: 1, textAlign: "center", fontSize: 60, fontWeight: 900, color: COL.DIM }}>X</div>
            <div style={{ flex: 2, textAlign: "center", fontSize: 52, fontWeight: 900, color: variant.fg, wordBreak: "keep-all", lineHeight: 1.1 }}>{ln}</div>
            <div style={{ flex: 1, textAlign: "center", fontSize: 60, fontWeight: 900, color: COL.ORANGE }}>✓</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
export const table: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
