import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { FONT, COL, clamp, easeOut, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Scene: React.FC<SceneProps> = ({ data, durFrames, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  const m = c.join(" ").match(/\d+/);
  const pct = Math.min(100, m ? parseInt(m[0], 10) : 100);
  const p = easeOut(clamp(frame / (durFrames * 0.75))) * pct;
  const r = 180, C = 2 * Math.PI * r;
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", alignItems: "center", flexDirection: "column" }}>
      <div style={{ position: "relative", width: 520, height: 520, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <svg width="520" height="520" viewBox="0 0 520 520">
          <circle cx="260" cy="260" r={r} fill="none" stroke="rgba(255,255,255,0.14)" strokeWidth="46" />
          <circle cx="260" cy="260" r={r} fill="none" stroke={variant.accent} strokeWidth="46" strokeLinecap="round" strokeDasharray={C} strokeDashoffset={C * (1 - p / 100)} transform="rotate(-90 260 260)" />
        </svg>
        <div style={{ position: "absolute", fontSize: 150, fontWeight: 900, color: variant.fg }}>{Math.round(p)}<span style={{ fontSize: 70 }}>%</span></div>
      </div>
      <div style={{ fontSize: 76, fontWeight: 900, color: variant.fg, marginTop: 30, textAlign: "center", wordBreak: "keep-all" }}>{c[c.length - 1]}</div>
    </AbsoluteFill>
  );
};
export const donut: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
