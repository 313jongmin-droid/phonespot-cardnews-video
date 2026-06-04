import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

interface SpecItem {
  label: string;
  value: string;
}

interface Props {
  items: SpecItem[];
}

export const SpecGrid: React.FC<Props> = ({ items }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        right: 60,
        bottom: 460,
        padding: "28px 24px",
        backgroundColor: "rgba(0,0,0,0.78)",
        borderRadius: 16,
        border: "2px solid rgba(247, 75, 11, 0.7)",
        color: "#FFFFFF",
        fontFamily: "'Pretendard', -apple-system, sans-serif",
      }}
    >
      <div
        style={{
          fontSize: 22,
          fontWeight: 700,
          color: "#F74B0B",
          letterSpacing: "0.12em",
          marginBottom: 18,
        }}
      >
        SPEC
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 14,
        }}
      >
        {items.map((it, i) => {
          const pop = spring({
            frame: frame - 14 - i * 5,
            fps,
            config: { damping: 13, stiffness: 200 },
          });
          const op = interpolate(frame, [14 + i * 5, 26 + i * 5], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={i}
              style={{
                padding: "14px 18px",
                backgroundColor: "rgba(247, 75, 11, 0.12)",
                borderLeft: "4px solid #F74B0B",
                borderRadius: 8,
                opacity: op,
                transform: `scale(${0.92 + pop * 0.08})`,
              }}
            >
              <div
                style={{
                  fontSize: 18,
                  fontWeight: 700,
                  color: "#F74B0B",
                  letterSpacing: "0.02em",
                  marginBottom: 4,
                }}
              >
                {it.label}
              </div>
              <div
                style={{
                  fontSize: 32,
                  fontWeight: 900,
                  letterSpacing: "-0.02em",
                  lineHeight: 1.1,
                }}
              >
                {it.value}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
