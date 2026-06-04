import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { FONT, COL, clamp, chunksOf, beatAt, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Scene: React.FC<SceneProps> = ({ data, durFrames, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  const { idx, lf, beatDur } = beatAt(frame, durFrames, c.length);
  const last = idx === c.length - 1;
  const draw = clamp(lf / (beatDur * 0.6));
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", alignItems: "center", padding: 90 }}>
      <div style={{ position: "relative", display: "inline-block" }}>
        <div style={{ fontSize: 118, fontWeight: 900, color: variant.fg, opacity: clamp(lf / 4), textAlign: "center", lineHeight: 1.1, letterSpacing: -1 }}>{c[idx]}</div>
        {last ? (
          <svg width="820" height="46" viewBox="0 0 820 46" style={{ position: "absolute", left: "50%", transform: "translateX(-50%)", bottom: -18 }}>
            <path d="M12 28 Q 210 8 410 24 T 808 20" stroke={variant.accent} strokeWidth="14" fill="none" strokeLinecap="round" strokeDasharray="900" strokeDashoffset={900 * (1 - draw)} />
          </svg>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
export const marker: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
