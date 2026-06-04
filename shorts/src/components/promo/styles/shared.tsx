import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export const FONT = "Pretendard, sans-serif";
export const COL = {
  WHITE: "#F4F1EA",   // 따뜻한 오프화이트
  INK: "#0E1116",     // 딥 차콜
  ORANGE: "#E0670F",  // 리파인드 앰버(브랜드)
  BLUE: "#9FB7C2",    // 스틸 톤(보조)
  RED: "#C2603F",     // 뮤트 테라코타
  YELLOW: "#E9C46A",  // 샴페인 골드
  DIM: "#8A8F99",     // 뮤트 그레이
  CREAM: "#EAD9C4",   // 샌드 베이지
};

// 섹션 순서(hook, fact1, fact2, fact3, cta)별 컬러 변주
export const VARIANTS: { bg: string; fg: string; accent: string }[] = [
  { bg: "#14181F", fg: COL.WHITE, accent: COL.ORANGE },   // hook  딥 그래파이트
  { bg: "#1B1417", fg: COL.WHITE, accent: COL.RED },       // 문제  딥 와인차콜 + 테라코타
  { bg: "#0F1F26", fg: COL.WHITE, accent: COL.YELLOW },    // 해결  딥 틸 + 골드
  { bg: "#14181F", fg: COL.WHITE, accent: COL.ORANGE },   // 신뢰
  { bg: "#9A3E0C", fg: COL.WHITE, accent: COL.CREAM },     // CTA  딥 앰버
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

// 두 스타일이 공유하는 CTA 블록 (브랜드 정보 — 결과는 동일하게 마무리)
export const CtaBlock: React.FC<{ data: any; ctaInfo?: CtaInfo }> = ({ data, ctaInfo }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const head = chunksOf(data);
  const a = (d: number) => interpolate(spring({ frame: frame - d, fps, config: { damping: 200 } }), [0, 1], [0, 1]);
  return (
    <AbsoluteFill
      style={{ backgroundColor: COL.ORANGE, fontFamily: FONT, justifyContent: "center", alignItems: "center" }}
    >
      <div style={{ fontSize: 72, fontWeight: 700, color: COL.CREAM, opacity: a(0) }}>{head[0] ?? "휴대폰도 이제"}</div>
      <div style={{ fontSize: 190, fontWeight: 900, color: COL.WHITE, opacity: a(6), marginBottom: 40 }}>
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
            color: COL.ORANGE,
            background: COL.WHITE,
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
        <div style={{ fontSize: 40, fontWeight: 700, color: COL.CREAM, marginTop: 22, opacity: a(30) }}>
          {ctaInfo.location}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// ---- 14종 스타일이 공유하는 추가 헬퍼 ----
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

export const BasicOutro: React.FC<{ durFrames: number }> = () => (
  <AbsoluteFill style={{ backgroundColor: COL.ORANGE, fontFamily: FONT, justifyContent: "center", alignItems: "center" }}>
    <div style={{ fontSize: 150, fontWeight: 900, color: COL.WHITE, letterSpacing: 3 }}>폰스팟</div>
  </AbsoluteFill>
);
