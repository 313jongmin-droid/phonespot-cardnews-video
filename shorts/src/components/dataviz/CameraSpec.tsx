import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

interface Lens {
  size: string;
  label: string;
  highlight?: boolean;
}

interface Props {
  lenses: Lens[];
}

export const CameraSpec: React.FC<Props> = ({ lenses }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const pulse = 1 + 0.05 * Math.sin(frame / 6);

  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        right: 60,
        bottom: 480,
        padding: "30px 24px",
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
          marginBottom: 16,
        }}
      >
        CAMERA · 3 LENS
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-around",
          alignItems: "flex-end",
          padding: "10px 0 4px",
        }}
      >
        {lenses.map((lens, i) => {
          const sizes = [180, 120, 100];
          const r = sizes[i] || 100;
          const enter = spring({
            frame: frame - 12 - i * 7,
            fps,
            config: { damping: 12, stiffness: 200 },
          });
          const scale = lens.highlight ? pulse : 1;
          return (
            <div key={i} style={{ textAlign: "center", transform: `scale(${enter})` }}>
              <div
                style={{
                  width: r,
                  height: r,
                  borderRadius: "50%",
                  background: lens.highlight
                    ? "radial-gradient(circle, #F74B0B 0%, #6F1F02 100%)"
                    : "radial-gradient(circle, #444 0%, #111 100%)",
                  border: lens.highlight ? "4px solid #FFD75A" : "3px solid #333",
                  boxShadow: lens.highlight ? "0 0 20px rgba(247,75,11,0.7)" : "none",
                  margin: "0 auto",
                  transform: `scale(${scale})`,
                }}
              />
              <div
                style={{
                  marginTop: 12,
                  fontSize: 32,
                  fontWeight: 900,
                  letterSpacing: "-0.02em",
                  color: lens.highlight ? "#F74B0B" : "#FFFFFF",
                }}
              >
                {lens.size}
              </div>
              <div
                style={{
                  fontSize: 18,
                  fontWeight: 600,
                  opacity: 0.75,
                  marginTop: 2,
                }}
              >
                {lens.label}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
