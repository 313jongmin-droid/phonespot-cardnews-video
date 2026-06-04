import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT, COL, clamp, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Scene: React.FC<SceneProps> = ({ data, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  const lit = [COL.YELLOW, COL.WHITE].includes(variant.accent);
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", alignItems: "center", padding: 90 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 38, width: "100%", alignItems: "center" }}>
        {c.map((ln, i) => {
          const s = spring({ frame: frame - i * 14, fps, config: { damping: 14 } });
          const last = i === c.length - 1;
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 30, opacity: clamp(interpolate(s, [0, 1], [0, 1])), transform: `scale(${interpolate(s, [0, 1], [0.6, 1])})` }}>
              <div style={{ width: 112, height: 112, borderRadius: 56, background: last ? variant.accent : "rgba(255,255,255,0.14)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 60, fontWeight: 900, color: last ? (lit ? COL.INK : COL.WHITE) : variant.fg }}>{i + 1}</div>
              <div style={{ fontSize: 70, fontWeight: 900, color: variant.fg, maxWidth: 640, lineHeight: 1.12 }}>{ln}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
export const steps: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
