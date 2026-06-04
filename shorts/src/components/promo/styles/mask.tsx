import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT, COL, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Scene: React.FC<SceneProps> = ({ data, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", alignItems: "center", padding: 110 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 16, alignItems: "center" }}>
        {c.map((ln, i) => {
          const s = spring({ frame: frame - 6 - i * 10, fps, config: { damping: 200 } });
          const ty = interpolate(s, [0, 1], [110, 0]);
          const last = i === c.length - 1;
          const size = last ? 128 : 92;
          return (
            <div key={i} style={{ overflow: "hidden", height: size * 1.18 }}>
              <div style={{ transform: `translateY(${ty}%)`, fontSize: size, fontWeight: 900, color: last ? variant.accent : variant.fg, lineHeight: 1.16, letterSpacing: -1 }}>{ln}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
export const mask: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
