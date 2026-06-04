import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT, COL, clamp, easeOut, chunksOf, CtaBlock, PromoStyle, SceneProps } from "./shared";

// 스타일 C: kinetic-box — "다른 편집자"가 만든 변형 키네틱.
// 시그니처: 한 구절씩 아래에서 슬라이드 인 + 핵심 구절은 하이라이트 박스,
//           하단 진행바 + 좌상단 브랜드 태그. (기존 kinetic의 가운데 스케일펀치와 구분)

const LIGHT_ACCENTS = [COL.YELLOW, COL.WHITE];
const textOnAccent = (accent: string) => (LIGHT_ACCENTS.includes(accent) ? COL.INK : COL.WHITE);

const Tag: React.FC<{ color: string }> = ({ color }) => (
  <div style={{ position: "absolute", top: 110, left: 90, fontSize: 40, fontWeight: 900, letterSpacing: 2, color, opacity: 0.85 }}>
    폰스팟
  </div>
);

const ProgressBar: React.FC<{ ratio: number; color: string }> = ({ ratio, color }) => (
  <div style={{ position: "absolute", left: 90, right: 90, bottom: 150, height: 10, borderRadius: 6, background: "rgba(255,255,255,0.22)" }}>
    <div style={{ width: `${clamp(ratio) * 100}%`, height: "100%", borderRadius: 6, background: color }} />
  </div>
);

const Phrase: React.FC<{ text: string; lf: number; accent: boolean; variant: SceneProps["variant"] }> = ({ text, lf, accent, variant }) => {
  const slide = (1 - easeOut(lf / 8)) * 90;
  const a = clamp(lf / 5);
  return (
    <div style={{ transform: `translateY(${slide}px)`, opacity: a, padding: "0 70px", textAlign: "center" }}>
      {accent ? (
        <span style={{ display: "inline-block", background: variant.accent, color: textOnAccent(variant.accent), fontSize: 118, fontWeight: 900, lineHeight: 1.1, padding: "14px 40px", borderRadius: 22, letterSpacing: -1 }}>
          {text}
        </span>
      ) : (
        <span style={{ fontSize: 100, fontWeight: 900, color: variant.fg, lineHeight: 1.12, letterSpacing: -1 }}>{text}</span>
      )}
    </div>
  );
};

const Opening: React.FC<{ line1: string; line2: string; durFrames: number }> = ({ line1, line2, durFrames }) => {
  const frame = useCurrentFrame();
  const half = durFrames / 2;
  const v = { bg: COL.INK, fg: COL.WHITE, accent: COL.ORANGE };
  return (
    <AbsoluteFill style={{ backgroundColor: COL.INK, fontFamily: FONT, justifyContent: "center", alignItems: "center" }}>
      <Tag color={COL.DIM} />
      {frame < half ? (
        <Phrase text={line1} lf={frame} accent={false} variant={{ ...v, fg: COL.DIM }} />
      ) : (
        <Phrase text={line2} lf={frame - half} accent variant={v} />
      )}
    </AbsoluteFill>
  );
};

const Scene: React.FC<SceneProps> = ({ data, durFrames, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const beats = chunksOf(data);
  const beatDur = durFrames / beats.length;
  const idx = Math.min(beats.length - 1, Math.floor(frame / beatDur));
  const lf = frame - idx * beatDur;
  const last = idx === beats.length - 1;
  const ratio = frame / durFrames;
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", alignItems: "center" }}>
      <Tag color={COL.DIM} />
      <Phrase text={beats[idx]} lf={lf} accent={last} variant={variant} />
      <ProgressBar ratio={ratio} color={variant.accent} />
    </AbsoluteFill>
  );
};

const Outro: React.FC<{ durFrames: number }> = () => {
  const frame = useCurrentFrame();
  const slide = (1 - easeOut(frame / 10)) * 80;
  return (
    <AbsoluteFill style={{ backgroundColor: COL.ORANGE, fontFamily: FONT, justifyContent: "center", alignItems: "center" }}>
      <div style={{ transform: `translateY(${slide}px)`, fontSize: 150, fontWeight: 900, color: COL.WHITE, letterSpacing: 3 }}>폰스팟</div>
      <div style={{ width: 220, height: 12, background: COL.WHITE, borderRadius: 6, marginTop: 28, opacity: clamp((frame - 6) / 8) }} />
    </AbsoluteFill>
  );
};

export const kineticBox: PromoStyle = { Opening, Scene, Outro };
