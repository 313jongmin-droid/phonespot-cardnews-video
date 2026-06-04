import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT, COL, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Scene: React.FC<SceneProps> = ({ data, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", alignItems: "center", padding: 90 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 30, width: "100%" }}>
        {c.map((ln, i) => {
          const s = spring({ frame: frame - i * 12, fps, config: { damping: 14 } });
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 30, background: "rgba(255,255,255,0.08)", border: `4px solid ${i === c.length - 1 ? variant.accent : "rgba(255,255,255,0.12)"}`, borderRadius: 28, padding: "34px 40px", opacity: interpolate(s, [0, 1], [0, 1]), transform: `scale(${interpolate(s, [0, 1], [0.8, 1])})` }}>
              <div style={{ width: 86, height: 86, minWidth: 86, borderRadius: 22, background: variant.accent, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 50, fontWeight: 900, color: COL.WHITE }}>✓</div>
              <div style={{ fontSize: 64, fontWeight: 900, color: variant.fg, wordBreak: "keep-all", lineHeight: 1.1 }}>{ln}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
export const statgrid: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
