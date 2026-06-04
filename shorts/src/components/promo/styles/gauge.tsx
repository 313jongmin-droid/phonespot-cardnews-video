import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { FONT, COL, clamp, easeOut, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const cx = 540, cy = 1000, r = 320, N = 48;
const pt = (th: number, rr: number) => ({ x: cx - rr * Math.cos(th), y: cy - rr * Math.sin(th) });
const seg = (rr: number, frac: number) => {
  let d = "";
  const last = Math.max(1, Math.round(N * clamp(frac)));
  for (let i = 0; i <= last; i++) { const p = pt((Math.PI * i) / N, rr); d += `${i ? "L" : "M"}${p.x.toFixed(1)} ${p.y.toFixed(1)} `; }
  return d;
};
const Scene: React.FC<SceneProps> = ({ data, durFrames, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  const p = easeOut(clamp(frame / (durFrames * 0.8)));
  const n = pt(Math.PI * p, r - 34);
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT }}>
      <svg width="1080" height="1920" viewBox="0 0 1080 1920" style={{ position: "absolute", inset: 0 }}>
        <path d={seg(r, 1)} fill="none" stroke="rgba(255,255,255,0.16)" strokeWidth="40" strokeLinecap="round" />
        <path d={seg(r, p)} fill="none" stroke={variant.accent} strokeWidth="40" strokeLinecap="round" />
        <line x1={cx} y1={cy} x2={n.x} y2={n.y} stroke={variant.fg} strokeWidth="16" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="26" fill={variant.fg} />
      </svg>
      <div style={{ position: "absolute", top: 1160, left: 0, right: 0, textAlign: "center", fontSize: 96, fontWeight: 900, color: variant.fg, wordBreak: "keep-all", padding: "0 80px" }}>{c[c.length - 1]}</div>
    </AbsoluteFill>
  );
};
export const gauge: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
