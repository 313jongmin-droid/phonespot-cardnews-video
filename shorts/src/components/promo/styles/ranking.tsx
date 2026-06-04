import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { FONT, COL, clamp, easeOut, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const WID = [1.0, 0.72, 0.52, 0.4];
const Scene: React.FC<SceneProps> = ({ data, durFrames, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", padding: "0 90px" }}>
      {c.map((ln, i) => {
        const w = easeOut(clamp((frame - i * 8) / 22)) * (WID[i] ?? 0.4) * 100;
        const top = i === 0;
        return (
          <div key={i} style={{ marginBottom: 30 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 10 }}>
              <span style={{ fontSize: 48, fontWeight: 900, color: top ? variant.accent : COL.DIM }}>{i + 1}</span>
              <span style={{ fontSize: 50, fontWeight: 900, color: variant.fg, wordBreak: "keep-all" }}>{ln}</span>
            </div>
            <div style={{ height: 56, borderRadius: 14, background: "rgba(255,255,255,0.1)" }}>
              <div style={{ width: `${w}%`, height: "100%", borderRadius: 14, background: top ? variant.accent : "rgba(255,255,255,0.3)" }} />
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
export const ranking: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
