import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

interface Line {
  text: string;
  accent?: boolean;
}

interface Props {
  topic: string;
  channelName: string;
  lines: Line[];
  meta: string;
}

export const NewsHeadlineOverlay: React.FC<Props> = ({
  topic,
  channelName,
  lines,
  meta,
}) => {
  const frame = useCurrentFrame();
  const barOp = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const hlY = interpolate(frame, [4, 16], [-24, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const hlOp = interpolate(frame, [4, 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const metaOp = interpolate(frame, [14, 24], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        top: 56,
        left: 48,
        right: 48,
        fontFamily:
          "'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
      }}
    >
      {/* 토픽 + 채널 */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          opacity: barOp,
          marginBottom: 20,
        }}
      >
        <div
          style={{
            fontSize: 30,
            fontWeight: 900,
            color: "#FFFFFF",
            backgroundColor: "#F74B0B",
            padding: "6px 20px",
            borderRadius: 6,
            letterSpacing: "0.04em",
          }}
        >
          {topic}
        </div>
        <div
          style={{
            fontSize: 36,
            fontWeight: 900,
            color: "#FFFFFF",
            letterSpacing: "-0.02em",
            textShadow: "0 2px 10px rgba(0,0,0,0.8)",
          }}
        >
          {channelName}
        </div>
      </div>

      {/* 헤드라인 */}
      <div style={{ opacity: hlOp, transform: `translateY(${hlY}px)` }}>
        {lines.map((line, i) => (
          <div
            key={i}
            style={{
              fontSize: 72,
              fontWeight: 900,
              letterSpacing: "-0.04em",
              lineHeight: 1.16,
              color: line.accent ? "#FFD24A" : "#FFFFFF",
              textShadow: "0 3px 16px rgba(0,0,0,0.85)",
            }}
          >
            {line.text}
          </div>
        ))}
      </div>

      {/* 메타 */}
      <div
        style={{
          marginTop: 14,
          fontSize: 25,
          fontWeight: 600,
          color: "rgba(255,255,255,0.78)",
          letterSpacing: "0.01em",
          opacity: metaOp,
          textShadow: "0 2px 8px rgba(0,0,0,0.9)",
        }}
      >
        {meta}
      </div>
    </div>
  );
};
