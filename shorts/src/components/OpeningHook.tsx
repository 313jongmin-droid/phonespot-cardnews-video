import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface Props {
  line1: string;
  line2: string;
  durFrames: number;
}

const line2Size = (line: string) => {
  const len = line.replace(/\s/g, "").length;
  if (len <= 9) return 104;
  if (len <= 13) return 92;
  return 82;
};

export const OpeningHook: React.FC<Props> = ({ line1, line2, durFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const l1op = interpolate(frame, [2, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const l1y = interpolate(frame, [2, 10], [-30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const l2 = spring({
    frame: frame - 7,
    fps,
    config: { damping: 11, stiffness: 240 },
  });
  const barW = interpolate(frame, [10, 22], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const zoom = interpolate(frame, [0, durFrames], [1.0, 1.035]);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#0A0A0A",
        justifyContent: "center",
        alignItems: "center",
        fontFamily:
          "'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
        transform: `scale(${zoom})`,
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(247,75,11,0.045) 1px, transparent 1px), linear-gradient(90deg, rgba(247,75,11,0.045) 1px, transparent 1px)",
          backgroundSize: "72px 72px",
        }}
      />

      <div style={{ textAlign: "center", padding: "0 70px" }}>
        <div
          style={{
            fontSize: 52,
            fontWeight: 700,
            color: "#FFFFFF",
            opacity: l1op * 0.85,
            transform: `translateY(${l1y}px)`,
            letterSpacing: 0,
          }}
        >
          {line1}
        </div>

        <div
          style={{
            width: `${barW}%`,
            height: 8,
            backgroundColor: "#F74B0B",
            margin: "26px auto",
            borderRadius: 4,
            maxWidth: 560,
          }}
        />

        <div
          style={{
            fontSize: line2Size(line2),
            fontWeight: 900,
            color: "#FFFFFF",
            letterSpacing: 0,
            lineHeight: 1.16,
            wordBreak: "keep-all",
            overflowWrap: "break-word",
            transform: `scale(${0.74 + l2 * 0.26})`,
          }}
        >
          {line2}
        </div>
      </div>
    </AbsoluteFill>
  );
};