import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT, COL, clamp, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Scene: React.FC<SceneProps> = ({ data, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", padding: "0 110px" }}>
      <div style={{ borderLeft: `16px solid ${variant.accent}`, paddingLeft: 48 }}>
        {c.map((ln, i) => {
          const s = spring({ frame: frame - i * 8, fps, config: { damping: 200 } });
          const last = i === c.length - 1;
          return (
            <div key={i} style={{ fontSize: last ? 100 : 60, fontWeight: last ? 900 : 700, color: last ? variant.fg : COL.DIM,
              opacity: interpolate(s, [0, 1], [0, 1]), transform: `translateX(${interpolate(s, [0, 1], [-40, 0])}px)`, lineHeight: 1.2, textAlign: "left", letterSpacing: -1 }}>{ln}</div>
          );
        })}
        <div style={{ height: 8, width: 240, background: variant.accent, marginTop: 36, opacity: clamp((frame - 20) / 10) }} />
      </div>
    </AbsoluteFill>
  );
};
export const swiss: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
