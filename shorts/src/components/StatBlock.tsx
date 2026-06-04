import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

interface Props {
  label: string;
  value: string;
  note?: string;
  color?: string;
  textColor?: string;
}

export const StatBlock: React.FC<Props> = ({
  label,
  value,
  note,
  color = "#F74B0B",
  textColor = "#FFFFFF",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = spring({
    frame: frame - 12,
    fps,
    config: { damping: 14, stiffness: 130 },
  });

  const opacity = interpolate(frame, [10, 22], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        right: 60,
        bottom: 460,
        padding: "32px 40px",
        backgroundColor: color,
        color: textColor,
        borderRadius: 16,
        fontFamily:
          "'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
        opacity,
        transform: `scale(${0.85 + enter * 0.15})`,
        transformOrigin: "center",
        boxShadow: "0 8px 32px rgba(0,0,0,0.25)",
      }}
    >
      <div
        style={{
          fontSize: 28,
          fontWeight: 700,
          letterSpacing: "0.05em",
          opacity: 0.88,
          textTransform: "uppercase",
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 116,
          fontWeight: 900,
          letterSpacing: "-0.04em",
          lineHeight: 1,
        }}
      >
        {value}
      </div>
      {note && (
        <div
          style={{
            fontSize: 30,
            fontWeight: 600,
            opacity: 0.85,
            marginTop: 10,
            letterSpacing: "-0.01em",
          }}
        >
          {note}
        </div>
      )}
    </div>
  );
};
