import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

interface Props {
  lines: string[];
  emphasisWords?: string[];
  durFrames: number;
}

// 나레이션 요약 문장을 하단에 정적으로 표시.
// 단어별 등장 없음 — 문장 통째로 페이드인. 강조어만 색 변경.
export const StaticSubtitle: React.FC<Props> = ({
  lines,
  emphasisWords = [],
  durFrames,
}) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [6, 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const y = interpolate(frame, [6, 18], [24, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const exit = interpolate(frame, [durFrames - 8, durFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const renderLine = (text: string, key: number) => {
    const words = text.split(/(\s+)/);
    return (
      <div key={key} style={{ display: "block" }}>
        {words.map((w, i) => {
          const clean = w.replace(/[.,!?·]/g, "").trim();
          const emph =
            clean.length > 0 &&
            emphasisWords.some((e) => clean.includes(e) || e.includes(clean));
          return (
            <span
              key={i}
              style={{
                color: "#FFFFFF",
              }}
            >
              {w}
            </span>
          );
        })}
      </div>
    );
  };

  return (
    <div
      style={{
        position: "absolute",
        left: 48,
        right: 48,
        bottom: 96,
        opacity: opacity * exit,
        transform: `translateY(${y}px)`,
        fontFamily:
          "'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
      }}
    >
      <div
        style={{
          backgroundColor: "rgba(10,10,10,0.82)",
          borderLeft: "8px solid #F74B0B",
          borderRadius: 6,
          padding: "26px 32px",
          fontSize: 52,
          fontWeight: 800,
          lineHeight: 1.36,
          letterSpacing: "-0.03em",
          textAlign: "left",
        }}
      >
        {lines.map((l, i) => renderLine(l, i))}
      </div>
    </div>
  );
};
