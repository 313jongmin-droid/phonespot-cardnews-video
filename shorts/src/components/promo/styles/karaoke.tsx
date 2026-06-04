import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { FONT, COL, clamp, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Scene: React.FC<SceneProps> = ({ data, durFrames, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const words = chunksOf(data).join(" ").split(" ").filter(Boolean);
  const prog = clamp(frame / durFrames);
  const visible = Math.floor(prog * words.length) + 1;
  const cur = Math.min(visible - 1, words.length - 1);
  const lit = [COL.YELLOW, COL.WHITE].includes(variant.accent);
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", alignItems: "center", padding: 110 }}>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "center", gap: "16px 18px", maxWidth: 880 }}>
        {words.map((w, i) => {
          const shown = i < visible;
          const isCur = i === cur;
          return (
            <span key={i} style={{ fontSize: 84, fontWeight: 900, lineHeight: 1.1, letterSpacing: -1,
              color: shown ? (isCur ? (lit ? COL.INK : COL.WHITE) : variant.fg) : "rgba(255,255,255,0.16)",
              background: isCur ? variant.accent : "transparent", borderRadius: 14, padding: isCur ? "6px 18px" : "6px 0" }}>{w}</span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
export const karaoke: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
