import React from "react";
import { AbsoluteFill } from "remotion";
import type { Script } from "./Composition";

// 9:16 Reels/Shorts 커버(정지컷). renderStill 로 1프레임만 렌더한다.
// 이미지 없이 타이포·컬러만 사용(라이브러리 그림 재사용/누적으로 커버가 서로 비슷해지는 문제 제거).
// 헤드라인: hook.headline_lines([{text},{text,accent}]) → 없으면 video_title 분할.
// 변형 3종을 slug 앞 숫자 %3 으로 자동 로테이션(피드에 나란히 놓여도 단조롭지 않게).
//   0=화이트 / 1=피치+하이라이트박스 / 2=오렌지 반전

const BRAND = "#F74B0B";
const PEACH = "#FFF1EA";
const INK = "#1A1A1A";
const WHITE = "#FFFFFF";
const FONT = "'Pretendard', -apple-system, 'Apple SD Gothic Neo', sans-serif";

type Variant = {
  bg: string;
  tag: string;
  tagOpacity: number;
  rule: string;
  badgeBg: string;
  badgeFg: string;
  badgeBorder: string;
  l1: string;
  l2Mode: "text" | "chip";
  l2Fg: string;
  l2Bg?: string;
  handle: string;
  handleOpacity: number;
  center: boolean;
};

const VARIANTS: Variant[] = [
  {
    bg: WHITE, tag: INK, tagOpacity: 0.6, rule: BRAND,
    badgeBg: BRAND, badgeFg: WHITE, badgeBorder: "none",
    l1: INK, l2Mode: "text", l2Fg: BRAND,
    handle: INK, handleOpacity: 0.55, center: false,
  },
  {
    bg: PEACH, tag: INK, tagOpacity: 0.6, rule: BRAND,
    badgeBg: WHITE, badgeFg: BRAND, badgeBorder: `3px solid ${BRAND}`,
    l1: INK, l2Mode: "chip", l2Fg: WHITE, l2Bg: BRAND,
    handle: INK, handleOpacity: 0.6, center: true,
  },
  {
    bg: BRAND, tag: WHITE, tagOpacity: 0.85, rule: WHITE,
    badgeBg: WHITE, badgeFg: BRAND, badgeBorder: "none",
    l1: WHITE, l2Mode: "chip", l2Fg: BRAND, l2Bg: WHITE,
    handle: WHITE, handleOpacity: 0.8, center: false,
  },
];

function variantIndex(slug: string): number {
  const s = String(slug || "");
  const m = s.match(/^(\d+)/);
  let n = 0;
  if (m) {
    n = parseInt(m[1], 10);
  } else {
    for (let i = 0; i < s.length; i++) n = (n + s.charCodeAt(i)) >>> 0;
  }
  return ((n % 3) + 3) % 3;
}

function pickHeadline(script: Script): { l1: string; l2: string } {
  const hl: any[] = (script.hook && (script.hook as any).headline_lines) || [];
  const l1 = (hl[0] && String(hl[0].text || "").trim()) || "";
  const l2 = (hl[1] && String(hl[1].text || "").trim()) || "";
  if (l1 || l2) return { l1, l2 };
  const t = String(script.video_title || script.title_short || "").trim();
  if (!t) return { l1: "", l2: "" };
  const words = t.split(/\s+/);
  if (words.length < 2) return { l1: t, l2: "" };
  const mid = Math.ceil(words.length / 2);
  return { l1: words.slice(0, mid).join(" "), l2: words.slice(mid).join(" ") };
}

export const CoverShort: React.FC<{ script: Script }> = ({ script }) => {
  const v = VARIANTS[variantIndex((script as any).slug || "")];
  const { l1, l2 } = pickHeadline(script);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: v.bg,
        fontFamily: FONT,
        display: "flex",
        flexDirection: "column",
        padding: 88,
        boxSizing: "border-box",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <div
          style={{
            backgroundColor: v.badgeBg,
            color: v.badgeFg,
            border: v.badgeBorder,
            fontWeight: 900,
            fontSize: 40,
            letterSpacing: -1,
            padding: "12px 28px",
            borderRadius: 18,
            boxSizing: "border-box",
          }}
        >
          {"폰스팟"}
        </div>
        <div style={{ color: v.tag, fontWeight: 700, fontSize: 30, opacity: v.tagOpacity }}>
          {"휴대폰성지 IT 브리핑"}
        </div>
      </div>

      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: v.center ? "center" : "flex-end",
          paddingBottom: v.center ? 0 : 40,
        }}
      >
        <div style={{ width: 110, height: 14, backgroundColor: v.rule, borderRadius: 8, marginBottom: 30 }} />
        {l1 ? (
          <div style={{ color: v.l1, fontWeight: 800, fontSize: 104, lineHeight: 1.14, letterSpacing: -3 }}>
            {l1}
          </div>
        ) : null}
        {l2 ? (
          <div style={{ marginTop: 18 }}>
            {v.l2Mode === "chip" ? (
              <span
                style={{
                  display: "inline-block",
                  backgroundColor: v.l2Bg,
                  color: v.l2Fg,
                  fontWeight: 900,
                  fontSize: 132,
                  lineHeight: 1.28,
                  letterSpacing: -3,
                  padding: "0 26px",
                  borderRadius: 22,
                }}
              >
                {l2}
              </span>
            ) : (
              <div style={{ color: v.l2Fg, fontWeight: 900, fontSize: 132, lineHeight: 1.1, letterSpacing: -3 }}>
                {l2}
              </div>
            )}
          </div>
        ) : null}
      </div>

      <div style={{ color: v.handle, fontWeight: 700, fontSize: 34, opacity: v.handleOpacity }}>
        {"@휴대폰성지폰스팟"}
      </div>
    </AbsoluteFill>
  );
};
