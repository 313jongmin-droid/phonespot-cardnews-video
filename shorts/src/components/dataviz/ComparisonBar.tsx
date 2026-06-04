import React from "react";
import { interpolate, useCurrentFrame } from "remotion";

interface Item {
  label: string;
  value: string;
  numeric: number;
  highlight?: boolean;
}

interface Props {
  items: Item[];
  title?: string;
}

export const ComparisonBar: React.FC<Props> = ({ items, title = "PRICE" }) => {
  const frame = useCurrentFrame();
  const maxV = Math.max(...items.map((i) => i.numeric));

  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        right: 60,
        bottom: 480,
        padding: "30px 28px",
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
          marginBottom: 22,
        }}
      >
        {title}
      </div>

      {items.map((item, i) => {
        const ratio = item.numeric / maxV;
        const grow = interpolate(frame, [16 + i * 12, 38 + i * 12], [0, ratio], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const op = interpolate(frame, [12 + i * 12, 22 + i * 12], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        return (
          <div key={i} style={{ marginBottom: 18, opacity: op }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
                marginBottom: 6,
              }}
            >
              <div
                style={{
                  fontSize: 24,
                  fontWeight: 700,
                  color: item.highlight ? "#F74B0B" : "rgba(255,255,255,0.7)",
                }}
              >
                {item.label}
              </div>
              <div
                style={{
                  fontSize: 30,
                  fontWeight: 900,
                  letterSpacing: "-0.02em",
                  color: item.highlight ? "#F74B0B" : "#FFFFFF",
                }}
              >
                {item.value}
              </div>
            </div>
            <div
              style={{
                height: 24,
                backgroundColor: "rgba(255,255,255,0.08)",
                borderRadius: 12,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${grow * 100}%`,
                  height: "100%",
                  background: item.highlight
                    ? "linear-gradient(90deg, #F74B0B 0%, #FF7A3D 100%)"
                    : "linear-gradient(90deg, #777 0%, #999 100%)",
                  borderRadius: 12,
                  transition: "none",
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};
