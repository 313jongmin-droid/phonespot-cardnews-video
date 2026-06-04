import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

export interface HeadlineLine {
  text: string;
  accent?: boolean;
}

interface Props {
  lines: HeadlineLine[];
  meta: string;
  bg?: string;
  accentColor?: string;
}

export const HeadlineBlock: React.FC<Props> = ({
  lines,
  meta,
  bg = "#15315C",
  accentColor = "#FFD24A",
}) => {
  const frame = useCurrentFrame();
  const slideIn = interpolate(frame, [2, 14], [-30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const opacity = interpolate(frame, [2, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const metaOpacity = interpolate(frame, [14, 24], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        backgroundColor: bg,
        padding: "36px 40px 30px",
        fontFamily:
          "'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
      }}
    >
      <div style={{ opacity, transform: `translateY(${slideIn}px)` }}>
        {lines.map((line, i) => (
          <div
            key={i}
            style={{
              fontSize: 78,
              fontWeight: 900,
              letterSpacing: "-0.04em",
              lineHeight: 1.18,
              color: line.accent ? accentColor : "#FFFFFF",
            }}
          >
            {line.text}
          </div>
        ))}
      </div>
      <div
        style={{
          marginTop: 18,
          fontSize: 26,
          fontWeight: 600,
          color: "rgba(255,255,255,0.62)",
          letterSpacing: "0.01em",
          opacity: metaOpacity,
        }}
      >
        {meta}
      </div>
    </div>
  );
};
