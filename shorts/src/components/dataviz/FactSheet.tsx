import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

interface Row {
  label: string;
  value: string;
  highlight?: boolean;
}

interface Props {
  title?: string;
  rows: Row[];
}

export const FactSheet: React.FC<Props> = ({ title = "FACT SHEET", rows }) => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        right: 60,
        bottom: 460,
        padding: "24px 28px",
        backgroundColor: "rgba(0,0,0,0.82)",
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
        {title}
      </div>

      {rows.map((row, i) => {
        const op = interpolate(frame, [10 + i * 5, 22 + i * 5], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const x = interpolate(frame, [10 + i * 5, 22 + i * 5], [-20, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        return (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "baseline",
              padding: "12px 0",
              borderBottom: i < rows.length - 1 ? "1px solid rgba(255,255,255,0.12)" : "none",
              opacity: op,
              transform: `translateX(${x}px)`,
            }}
          >
            <div
              style={{
                width: "38%",
                fontSize: 24,
                fontWeight: 700,
                color: "rgba(255,255,255,0.65)",
                letterSpacing: "-0.01em",
              }}
            >
              {row.label}
            </div>
            <div
              style={{
                flex: 1,
                fontSize: row.highlight ? 36 : 32,
                fontWeight: 900,
                color: row.highlight ? "#F74B0B" : "#FFFFFF",
                letterSpacing: "-0.02em",
                textAlign: "right",
              }}
            >
              {row.value}
            </div>
          </div>
        );
      })}
    </div>
  );
};
