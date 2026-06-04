import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT, COL, clamp, easeBack, chunksOf, CtaBlock, PromoStyle, SceneProps } from "./shared";

// 스타일 B: 비트컷 — 한 화면에 한 구절씩 빠르게 끊어치며 펀치인 (현대 숏폼/광고 톤)
const Beat: React.FC<{ text: string; size: number; color: string; bg: string; lf: number; punch?: boolean }> = ({ text, size, color, bg, lf, punch }) => {
  const a = clamp(lf / 4);
  const sc = easeBack(lf / (punch ? 7 : 6));
  const s = 0.6 + 0.4 * Math.min(sc, 1.12);
  return (
    <AbsoluteFill style={{ backgroundColor: bg, fontFamily: FONT, justifyContent: "center", alignItems: "center" }}>
      <div style={{ transform: `scale(${s})`, opacity: a, fontSize: size, fontWeight: 900, color, textAlign: "center", letterSpacing: -1, padding: "0 80px" }}>{text}</div>
    </AbsoluteFill>
  );
};

const Opening: React.FC<{ line1: string; line2: string; durFrames: number }> = ({ line1, line2, durFrames }) => {
  const frame = useCurrentFrame();
  const half = durFrames / 2;
  if (frame < half) return <Beat text={line1} size={84} color={COL.DIM} bg={COL.INK} lf={frame} />;
  return <Beat text={line2} size={130} color={COL.ORANGE} bg={COL.INK} lf={frame - half} punch />;
};

const Scene: React.FC<SceneProps> = ({ data, durFrames, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const beats = chunksOf(data);
  const beatDur = durFrames / beats.length;
  const idx = Math.min(beats.length - 1, Math.floor(frame / beatDur));
  const lf = frame - idx * beatDur;
  const last = idx === beats.length - 1;
  return (
    <Beat
      text={beats[idx]}
      size={last ? 132 : 100}
      color={last ? variant.accent : variant.fg}
      bg={variant.bg}
      lf={lf}
      punch={last}
    />
  );
};

const Outro: React.FC<{ durFrames: number }> = () => {
  const frame = useCurrentFrame();
  return <Beat text="폰스팟" size={150} color={COL.WHITE} bg={COL.ORANGE} lf={frame} punch />;
};

export const kinetic: PromoStyle = { Opening, Scene, Outro };
