import React from "react";
import { AbsoluteFill } from "remotion";

export type Emotion =
  | "surprised"
  | "satisfied"
  | "suspicious"
  | "smirk"
  | "serious"
  | "wink"
  | "excited"
  | "confused"
  | "shocked"
  | "thinking"
  | "sleepy"
  | "angry";

interface Props {
  emotion: Emotion;
}

// 폰스팟 B급 마스코트 - 페페풍 비대칭 윤곽 + 처진 눈 + 늘어진 입.
const OUTLINE =
  "M22 110 Q14 44 86 36 Q170 40 162 108 Q166 168 88 176 Q18 170 22 110 Z";

const Face: React.FC<{ emotion: Emotion }> = ({ emotion }) => {
  switch (emotion) {
    case "surprised":
      return (
        <>
          <ellipse cx="62" cy="86" rx="34" ry="36" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <ellipse cx="120" cy="84" rx="30" ry="33" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <circle cx="64" cy="74" r="9" fill="#1A1A1A" />
          <circle cx="121" cy="73" r="8" fill="#1A1A1A" />
          <path d="M48 132 Q92 158 138 128 Q96 150 48 132 Z" fill="#7a2406" stroke="#8a2a06" strokeWidth="3" />
        </>
      );
    case "satisfied":
      return (
        <>
          <ellipse cx="60" cy="88" rx="32" ry="30" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <ellipse cx="118" cy="86" rx="29" ry="28" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <path d="M40 84 Q60 70 80 86" stroke="#1A1A1A" strokeWidth="7" fill="none" strokeLinecap="round" />
          <path d="M96 82 Q118 70 138 86" stroke="#1A1A1A" strokeWidth="7" fill="none" strokeLinecap="round" />
          <path d="M44 126 Q92 168 142 120 Q96 142 44 126 Z" fill="#7a2406" stroke="#8a2a06" strokeWidth="3" />
        </>
      );
    case "suspicious":
      return (
        <>
          <ellipse cx="62" cy="90" rx="33" ry="26" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <ellipse cx="120" cy="88" rx="30" ry="24" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <circle cx="72" cy="90" r="8" fill="#1A1A1A" />
          <circle cx="129" cy="88" r="7" fill="#1A1A1A" />
          <path d="M36 64 Q60 56 86 70" stroke="#8a2a06" strokeWidth="6" fill="none" strokeLinecap="round" />
          <path d="M148 62 Q124 56 100 70" stroke="#8a2a06" strokeWidth="6" fill="none" strokeLinecap="round" />
          <path d="M58 134 Q92 124 132 138" stroke="#7a2406" strokeWidth="9" fill="none" strokeLinecap="round" />
        </>
      );
    case "smirk":
      return (
        <>
          <ellipse cx="60" cy="88" rx="32" ry="27" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <ellipse cx="118" cy="86" rx="29" ry="25" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <path d="M40 88 L82 86" stroke="#1A1A1A" strokeWidth="7" fill="none" strokeLinecap="round" />
          <path d="M98 86 L138 84" stroke="#1A1A1A" strokeWidth="7" fill="none" strokeLinecap="round" />
          <path d="M46 124 Q96 156 144 112 Q98 140 46 124 Z" fill="#7a2406" stroke="#8a2a06" strokeWidth="3" />
        </>
      );
    case "serious":
      return (
        <>
          <ellipse cx="62" cy="88" rx="32" ry="29" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <ellipse cx="120" cy="86" rx="29" ry="27" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <rect x="46" y="84" width="34" height="9" rx="3" fill="#1A1A1A" />
          <rect x="104" y="82" width="32" height="9" rx="3" fill="#1A1A1A" />
          <path d="M56 134 L132 130" stroke="#7a2406" strokeWidth="9" fill="none" strokeLinecap="round" />
        </>
      );
    case "wink":
      return (
        <>
          <ellipse cx="60" cy="88" rx="32" ry="29" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <path d="M38 88 Q60 72 84 88" stroke="#1A1A1A" strokeWidth="8" fill="none" strokeLinecap="round" />
          <ellipse cx="120" cy="86" rx="30" ry="30" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <circle cx="122" cy="84" r="9" fill="#1A1A1A" />
          <path d="M48 128 Q94 160 140 122 Q96 144 48 128 Z" fill="#7a2406" stroke="#8a2a06" strokeWidth="3" />
        </>
      );
    case "excited":
      return (
        <>
          <ellipse cx="60" cy="88" rx="32" ry="32" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <ellipse cx="118" cy="86" rx="30" ry="30" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          {/* 별 모양 눈 */}
          <path d="M60 76 L64 86 L74 86 L66 92 L70 102 L60 96 L50 102 L54 92 L46 86 L56 86 Z" fill="#1A1A1A" />
          <path d="M118 74 L122 84 L132 84 L124 90 L128 100 L118 94 L108 100 L112 90 L104 84 L114 84 Z" fill="#1A1A1A" />
          <ellipse cx="92" cy="138" rx="46" ry="22" fill="#7a2406" stroke="#8a2a06" strokeWidth="3" />
          <path d="M46 138 L138 138" stroke="#fff" strokeWidth="3" fill="none" />
        </>
      );
    case "confused":
      return (
        <>
          <ellipse cx="62" cy="90" rx="32" ry="27" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <ellipse cx="120" cy="86" rx="30" ry="27" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <circle cx="64" cy="92" r="8" fill="#1A1A1A" />
          <circle cx="122" cy="86" r="8" fill="#1A1A1A" />
          {/* 비대칭 눈썹 - 한쪽만 올라감 */}
          <path d="M38 70 Q62 60 86 72" stroke="#8a2a06" strokeWidth="6" fill="none" strokeLinecap="round" />
          <path d="M100 56 Q122 50 142 62" stroke="#8a2a06" strokeWidth="6" fill="none" strokeLinecap="round" />
          {/* 비뚤어진 입 */}
          <path d="M52 138 Q80 124 96 142 Q112 134 134 132" stroke="#7a2406" strokeWidth="8" fill="none" strokeLinecap="round" />
        </>
      );
    case "shocked":
      return (
        <>
          <ellipse cx="60" cy="84" rx="36" ry="40" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <ellipse cx="120" cy="82" rx="32" ry="36" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <circle cx="62" cy="76" r="10" fill="#1A1A1A" />
          <circle cx="120" cy="74" r="9" fill="#1A1A1A" />
          {/* O 모양 입 */}
          <ellipse cx="92" cy="142" rx="20" ry="24" fill="#3a0e02" stroke="#8a2a06" strokeWidth="3" />
        </>
      );
    case "thinking":
      return (
        <>
          <ellipse cx="62" cy="88" rx="32" ry="29" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <ellipse cx="120" cy="86" rx="29" ry="27" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          {/* 위로 향한 시선 */}
          <circle cx="68" cy="78" r="8" fill="#1A1A1A" />
          <circle cx="126" cy="76" r="7" fill="#1A1A1A" />
          {/* 다문 입 한쪽 올림 */}
          <path d="M48 132 Q88 122 116 136" stroke="#7a2406" strokeWidth="8" fill="none" strokeLinecap="round" />
        </>
      );
    case "sleepy":
      return (
        <>
          <ellipse cx="60" cy="92" rx="32" ry="14" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <ellipse cx="118" cy="90" rx="30" ry="13" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          {/* 감은 눈 */}
          <path d="M32 92 Q60 96 88 90" stroke="#1A1A1A" strokeWidth="6" fill="none" strokeLinecap="round" />
          <path d="M92 90 Q118 94 144 88" stroke="#1A1A1A" strokeWidth="6" fill="none" strokeLinecap="round" />
          {/* 작은 다문 입 */}
          <ellipse cx="92" cy="138" rx="20" ry="6" fill="#7a2406" stroke="#8a2a06" strokeWidth="3" />
        </>
      );
    case "angry":
      return (
        <>
          <ellipse cx="62" cy="92" rx="32" ry="26" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          <ellipse cx="120" cy="90" rx="30" ry="26" fill="#fff" stroke="#8a2a06" strokeWidth="3" />
          {/* V자 눈썹 */}
          <path d="M34 70 L86 88" stroke="#8a2a06" strokeWidth="8" fill="none" strokeLinecap="round" />
          <path d="M150 68 L100 86" stroke="#8a2a06" strokeWidth="8" fill="none" strokeLinecap="round" />
          <circle cx="64" cy="96" r="8" fill="#1A1A1A" />
          <circle cx="120" cy="94" r="7" fill="#1A1A1A" />
          {/* 찡그린 입 */}
          <path d="M48 144 L92 132 L138 142" stroke="#7a2406" strokeWidth="9" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </>
      );
  }
};

// 소품 (emotion에 따라 마스코트 옆에 자동 배치)
const Prop: React.FC<{ emotion: Emotion }> = ({ emotion }) => {
  const t = {
    fontFamily: "'Pretendard', sans-serif",
    fontWeight: 900,
    fill: "#F74B0B",
    stroke: "#fff",
    strokeWidth: 4,
    paintOrder: "stroke" as const,
  };
  switch (emotion) {
    case "excited":
      return (
        <>
          <text x="14" y="40" fontSize="36" {...t}>★</text>
          <text x="158" y="50" fontSize="32" {...t}>✦</text>
          <text x="20" y="200" fontSize="28" {...t}>✨</text>
        </>
      );
    case "confused":
      return <text x="148" y="36" fontSize="56" {...t}>?</text>;
    case "shocked":
      return <text x="150" y="40" fontSize="58" {...t}>!</text>;
    case "thinking":
      return (
        <>
          <ellipse cx="166" cy="32" rx="22" ry="14" fill="#fff" stroke="#8a2a06" strokeWidth="2" />
          <circle cx="148" cy="48" r="4" fill="#fff" stroke="#8a2a06" strokeWidth="2" />
          <text x="156" y="38" fontSize="20" fontWeight="700" fill="#1A1A1A">?</text>
        </>
      );
    case "sleepy":
      return (
        <>
          <text x="140" y="40" fontSize="28" {...t}>Z</text>
          <text x="160" y="60" fontSize="22" {...t}>z</text>
          <text x="172" y="76" fontSize="18" {...t}>z</text>
        </>
      );
    case "angry":
      return <text x="148" y="40" fontSize="44" {...t}>#@!</text>;
    default:
      return null;
  }
};

export const Mascot: React.FC<Props> = ({ emotion }) => {
  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#FFF1EA",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <svg width="58%" viewBox="0 0 200 210" xmlns="http://www.w3.org/2000/svg">
        <path d={OUTLINE} fill="#F74B0B" stroke="#8a2a06" strokeWidth="4" />
        <Face emotion={emotion} />
        <Prop emotion={emotion} />
      </svg>
    </AbsoluteFill>
  );
};
