import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { FONT, COL, clamp, easeOut, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const PTS = [0.18, 0.4, 0.32, 0.6, 0.82, 1.0];
const Scene: React.FC<SceneProps> = ({ data, durFrames, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  const prog = easeOut(clamp(frame / (durFrames * 0.8)));
  const x0 = 120, x1 = 960, y0 = 1280, y1 = 620;
  const pts = PTS.map((v, i) => ({ x: x0 + (x1 - x0) * (i / (PTS.length - 1)), y: y0 - (y0 - y1) * v }));
  const shownN = Math.max(1, Math.floor(prog * pts.length));
  const path = pts.slice(0, shownN).map((p, i) => `${i ? "L" : "M"}${p.x} ${p.y}`).join(" ");
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center" }}>
      <svg width="1080" height="1920" viewBox="0 0 1080 1920" style={{ position: "absolute", inset: 0 }}>
        <line x1={x0} y1={y0} x2={x1} y2={y0} stroke="rgba(255,255,255,0.2)" strokeWidth="4" />
        <path d={path} fill="none" stroke={variant.accent} strokeWidth="14" strokeLinecap="round" strokeLinejoin="round" />
        {pts.slice(0, shownN).map((p, i) => (<circle key={i} cx={p.x} cy={p.y} r={i === pts.length - 1 ? 22 : 12} fill={i === pts.length - 1 ? variant.accent : variant.fg} />))}
      </svg>
      <div style={{ position: "absolute", top: 360, left: 0, right: 0, textAlign: "center", fontSize: 88, fontWeight: 900, color: variant.fg, wordBreak: "keep-all", padding: "0 80px" }}>{c[c.length - 1]}</div>
    </AbsoluteFill>
  );
};
export const linegraph: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
