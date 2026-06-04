import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

interface TimelinePoint {
  date: string;
  label: string;
  highlight?: boolean;
}

interface Props {
  points: TimelinePoint[];
}

export const Timeline: React.FC<Props> = ({ points }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const lineProgress = interpolate(frame, [12, 40], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        right: 60,
        bottom: 540,
        padding: "32px 28px",
        backgroundColor: "rgba(0,0,0,0.78)",
        borderRadius: 16,
        border: "2px solid rgba(247, 75, 11, 0.7)",
        color: "#FFFFFF",
        fontFamily:
          "'Pretendard', -apple-system, sans-serif",
      }}
    >
      <div
        style={{
          fontSize: 22,
          fontWeight: 700,
          color: "#F74B0B",
          letterSpacing: "0.12em",
          marginBottom: 22,
        }}
      >
        TIMELINE
      </div>

      <div style={{ position: "relative", height: 110 }}>
        <div
          style={{
            position: "absolute",
            top: 20,
            left: 0,
            right: 0,
            height: 4,
            backgroundColor: "rgba(255,255,255,0.15)",
            borderRadius: 2,
          }}
        />
        <div
          style={{
            position: "absolute",
            top: 20,
            left: 0,
            width: `${lineProgress}%`,
            height: 4,
            backgroundColor: "#F74B0B",
            borderRadius: 2,
          }}
        />
        {points.map((p, i) => {
          const x = (i / Math.max(1, points.length - 1)) * 100;
          const pop = spring({
            frame: frame - 18 - i * 6,
            fps,
            config: { damping: 12, stiffness: 220 },
          });
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: `${x}%`,
                top: 0,
                transform: `translateX(-50%) scale(${pop})`,
              }}
            >
              <div
                style={{
                  width: p.highlight ? 36 : 28,
                  height: p.highlight ? 36 : 28,
                  borderRadius: "50%",
                  backgroundColor: p.highlight ? "#F74B0B" : "#FFFFFF",
                  border: p.highlight ? "4px solid #FFFFFF" : "none",
                  margin: p.highlight ? "2px auto" : "6px auto",
                  boxShadow: p.highlight ? "0 0 0 6px rgba(247,75,11,0.3)" : "none",
                }}
              />
              <div
                style={{
                  marginTop: 10,
                  textAlign: "center",
                  fontSize: 26,
                  fontWeight: 900,
                  letterSpacing: "-0.02em",
                  color: p.highlight ? "#F74B0B" : "#FFFFFF",
                  whiteSpace: "nowrap",
                }}
              >
                {p.date}
              </div>
              <div
                style={{
                  textAlign: "center",
                  fontSize: 18,
                  fontWeight: 600,
                  opacity: 0.8,
                  marginTop: 2,
                  whiteSpace: "nowrap",
                }}
              >
                {p.label}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
