import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT, COL, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Scene: React.FC<SceneProps> = ({ data, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  const mark = "✓"; // ✓
  const mc = COL.ORANGE;
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", padding: "0 110px" }}>
      {c.map((ln, i) => {
        const s = spring({ frame: frame - i * 12, fps, config: { damping: 200 } });
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 34, marginBottom: 46, opacity: interpolate(s, [0, 1], [0, 1]), transform: `translateX(${interpolate(s, [0, 1], [-30, 0])}px)` }}>
            <div style={{ minWidth: 96, width: 96, height: 96, borderRadius: 24, background: mc, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 60, fontWeight: 900, color: COL.WHITE }}>{mark}</div>
            <div style={{ fontSize: 74, fontWeight: 900, color: variant.fg, lineHeight: 1.15, wordBreak: "keep-all" }}>{ln}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
export const checklist: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
