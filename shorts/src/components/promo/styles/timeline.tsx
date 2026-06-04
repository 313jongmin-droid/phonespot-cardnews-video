import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT, COL, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Scene: React.FC<SceneProps> = ({ data, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", padding: "0 120px" }}>
      <div style={{ position: "relative", paddingLeft: 80 }}>
        <div style={{ position: "absolute", left: 26, top: 20, bottom: 20, width: 8, background: "rgba(255,255,255,0.2)", borderRadius: 4 }} />
        {c.map((ln, i) => {
          const s = spring({ frame: frame - i * 12, fps, config: { damping: 200 } });
          const last = i === c.length - 1;
          return (
            <div key={i} style={{ position: "relative", display: "flex", alignItems: "center", minHeight: 120, opacity: interpolate(s, [0, 1], [0, 1]), transform: `translateX(${interpolate(s, [0, 1], [30, 0])}px)` }}>
              <div style={{ position: "absolute", left: -64, width: 44, height: 44, borderRadius: 22, background: last ? variant.accent : variant.fg }} />
              <div style={{ fontSize: last ? 92 : 70, fontWeight: 900, color: last ? variant.accent : variant.fg, lineHeight: 1.15 }}>{ln}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
export const timeline: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
