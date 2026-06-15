import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export const FONT = "Pretendard, sans-serif";

// ★ 3색 체계 (세련): 검정 바탕 + 흰색 주체 + 오렌지 강조(10%만).
// COL 키는 기존 컴포넌트 호환 위해 유지하되 값은 3색으로 수렴 — 보조색(RED/YELLOW→오렌지, CREAM→화이트, BLUE/DIM→중립그레이).
export const COL = {
  WHITE: "#FFFFFF",   // 주체(제목·본문)
  INK: "#0E0E10",     // 바탕(딥 블랙, 순흑보다 살짝 들어 밴딩↓)
  ORANGE: "#FF5A1F",  // 단일 강조(밝은 오렌지)
  BLUE: "#8C8C92",    // (수렴) 중립 그레이
  RED: "#FF5A1F",     // (수렴) 오렌지
  YELLOW: "#FF5A1F",  // (수렴) 오렌지
  DIM: "#8C8C92",     // 보조 텍스트용 중립 그레이(검정/흰색 사이 톤)
  CREAM: "#FFFFFF",   // (수렴) 화이트
};

// 섹션 순서(hook, fact1, fact2, fact3, cta)별 변주 — 3색 체계라 바탕=검정 고정, 강조만 오렌지.
export const VARIANTS: { bg: string; fg: string; accent: string }[] = [
  { bg: COL.INK, fg: COL.WHITE, accent: COL.ORANGE },
  { bg: COL.INK, fg: COL.WHITE, accent: COL.ORANGE },
  { bg: COL.INK, fg: COL.WHITE, accent: COL.ORANGE },
  { bg: COL.INK, fg: COL.WHITE, accent: COL.ORANGE },
  { bg: COL.INK, fg: COL.WHITE, accent: COL.ORANGE },
];
export const variantFor = (i: number) => VARIANTS[Math.min(i, VARIANTS.length - 1)];

export const clamp = (t: number) => Math.min(Math.max(t, 0), 1);
export const easeOut = (t: number) => 1 - Math.pow(1 - clamp(t), 3);
export const easeBack = (t: number) => {
  t = clamp(t);
  const c1 = 2.0;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
};

export const chunksOf = (data: any): string[] => {
  if (Array.isArray(data?.caption_chunks) && data.caption_chunks.length) return data.caption_chunks;
  if (Array.isArray(data?.headline_lines) && data.headline_lines.length)
    return data.headline_lines.map((l: any) => l.text);
  return [String(data?.topic ?? "")];
};

export interface CtaInfo {
  kakao?: string;
  litt?: string;
  location?: string;
}
export interface SceneProps {
  data: any;
  durFrames: number;
  variant: { bg: string; fg: string; accent: string };
  isCta?: boolean;
  ctaInfo?: CtaInfo;
}
export interface PromoStyle {
  Opening: React.FC<{ line1: string; line2: string; durFrames: number }>;
  Scene: React.FC<SceneProps>;
  Outro: React.FC<{ durFrames: number }>;
}

// 공유 CTA 블록 — 검정 바탕 + 흰색 주체 + 오렌지 강조(핵심 단어·litt 버튼만).
export const CtaBlock: React.FC<{ data: any; ctaInfo?: CtaInfo }> = ({ data, ctaInfo }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const head = chunksOf(data);
  const a = (d: number) => interpolate(spring({ frame: frame - d, fps, config: { damping: 200 } }), [0, 1], [0, 1]);
  return (
    <AbsoluteFill
      style={{ backgroundColor: COL.INK, fontFamily: FONT, justifyContent: "center", alignItems: "center" }}
    >
      <div style={{ fontSize: 72, fontWeight: 700, color: COL.DIM, opacity: a(0) }}>{head[0] ?? "휴대폰도 이제"}</div>
      <div style={{ fontSize: 190, fontWeight: 900, color: COL.ORANGE, opacity: a(6), marginBottom: 40 }}>
        {head[1] ?? "정찰제"}
      </div>
      <div style={{ fontSize: 92, fontWeight: 900, color: COL.WHITE, letterSpacing: 2, opacity: a(16) }}>폰스팟</div>
      {ctaInfo?.kakao ? (
        <div style={{ fontSize: 44, fontWeight: 700, color: COL.WHITE, marginTop: 18, opacity: a(22) }}>
          카카오톡 {ctaInfo.kakao}
        </div>
      ) : null}
      {ctaInfo?.litt ? (
        <div
          style={{
            fontSize: 52,
            fontWeight: 900,
            color: COL.WHITE,
            background: COL.ORANGE,
            borderRadius: 60,
            padding: "22px 56px",
            marginTop: 26,
            opacity: a(26),
          }}
        >
          {ctaInfo.litt}
        </div>
      ) : null}
      {ctaInfo?.location ? (
        <div style={{ fontSize: 40, fontWeight: 700, color: COL.DIM, marginTop: 22, opacity: a(30) }}>
          {ctaInfo.location}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// ---- 스타일 공용 헬퍼 ----
export const beatAt = (frame: number, durFrames: number, count: number) => {
  const n = Math.max(1, count);
  const beatDur = durFrames / n;
  const idx = Math.min(n - 1, Math.floor(frame / beatDur));
  return { idx, lf: frame - idx * beatDur, beatDur };
};

export const BasicOpening: React.FC<{ line1: string; line2: string; durFrames: number }> = ({ line1, line2 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = (d: number) => spring({ frame: frame - d, fps, config: { damping: 200 } });
  return (
    <AbsoluteFill style={{ backgroundColor: COL.INK, fontFamily: FONT, justifyContent: "center", alignItems: "center", gap: 18 }}>
      <div style={{ fontSize: 68, fontWeight: 700, color: COL.DIM, opacity: interpolate(a(0), [0, 1], [0, 1]), transform: `translateY(${interpolate(a(0), [0, 1], [40, 0])}px)` }}>{line1}</div>
      <div style={{ fontSize: 120, fontWeight: 900, color: COL.ORANGE, opacity: interpolate(a(8), [0, 1], [0, 1]), transform: `translateY(${interpolate(a(8), [0, 1], [40, 0])}px)` }}>{line2}</div>
    </AbsoluteFill>
  );
};

// 아웃트로 — 검정 바탕 + 흰색 로고 + 오렌지 언더라인(강조 1점).
export const BasicOutro: React.FC<{ durFrames: number }> = () => (
  <AbsoluteFill style={{ backgroundColor: COL.INK, fontFamily: FONT, justifyContent: "center", alignItems: "center", gap: 28 }}>
    <div style={{ fontSize: 150, fontWeight: 900, color: COL.WHITE, letterSpacing: 3 }}>폰스팟</div>
    <div style={{ width: 120, height: 12, borderRadius: 6, backgroundColor: COL.ORANGE }} />
  </AbsoluteFill>
);
