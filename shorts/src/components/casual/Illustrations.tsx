import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

const SHELL: React.CSSProperties = {
  backgroundColor: "#FFF1EA",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: 40,
  boxSizing: "border-box",
  overflow: "hidden",
};

const hashVariant = (value: string) =>
  value.split("").reduce((sum, ch) => sum + ch.charCodeAt(0), 0);

const AmbientUnderlay: React.FC<{ variant: string }> = ({ variant }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const seed = hashVariant(variant);
  const cycle = Math.max(1, fps * (9 + (seed % 5)));
  const t = (frame % cycle) / cycle;
  const driftX = interpolate(t, [0, 1], [-22 + (seed % 9), 22 - (seed % 7)]);
  const driftY = interpolate(t, [0, 1], [12 - (seed % 5), -14 + (seed % 6)]);
  const glowX = interpolate(t, [0, 1], [18, 82]);
  const glowY = interpolate(t, [0, 1], [16 + (seed % 14), 48 + (seed % 10)]);

  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: "#FFF1EA" }}>
      <AbsoluteFill
        style={{
          opacity: 0.42,
          transform: `translate(${driftX}px, ${driftY}px)`,
          backgroundImage:
            "linear-gradient(rgba(247,75,11,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(247,75,11,0.05) 1px, transparent 1px)",
          backgroundSize: "46px 46px",
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at ${glowX}% ${glowY}%, rgba(247,75,11,0.22), rgba(247,75,11,0.08) 24%, transparent 56%)`,
          opacity: 0.76,
        }}
      />
    </AbsoluteFill>
  );
};

const SurfaceOverlay: React.FC<{ variant: string }> = ({ variant }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const seed = hashVariant(variant);
  const cycle = Math.max(1, fps * (6 + (seed % 4)));
  const t = (frame % cycle) / cycle;
  const sweep = interpolate(t, [0, 1], [-32, 132]);
  const grainX = interpolate(t, [0, 1], [0, 18 + (seed % 8)]);
  const grainY = interpolate(t, [0, 1], [0, -14 - (seed % 6)]);
  const pulse = 0.5 + Math.sin((frame / Math.max(1, fps)) * 1.2 + seed) * 0.5;

  return (
    <AbsoluteFill style={{ pointerEvents: "none", zIndex: 2, overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          opacity: 0.16 + pulse * 0.05,
          backgroundImage:
            "radial-gradient(rgba(26,26,26,0.10) 0.75px, transparent 0.75px)",
          backgroundSize: "7px 7px",
          transform: `translate(${grainX}px, ${grainY}px)`,
          mixBlendMode: "multiply",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: `${sweep}%`,
          top: -80,
          width: 120,
          height: "130%",
          transform: "skewX(-15deg)",
          background:
            "linear-gradient(90deg, transparent, rgba(255,255,255,0.46), transparent)",
          opacity: 0.46,
          mixBlendMode: "screen",
        }}
      />
      <AbsoluteFill
        style={{
          opacity: 0.18,
          background:
            "linear-gradient(180deg, rgba(255,255,255,0.16), transparent 36%, rgba(247,75,11,0.06))",
        }}
      />
    </AbsoluteFill>
  );
};

export const Illust: React.FC<{ variant: string; animatedBackground?: boolean }> = ({
  variant,
  animatedBackground = false,
}) => {
  return (
    <AbsoluteFill style={SHELL}>
      {animatedBackground && <AmbientUnderlay variant={variant} />}
      <Img
        src={staticFile(`assets/illustrations/${variant}.png`)}
        style={{
          maxWidth: "92%",
          maxHeight: "92%",
          objectFit: "contain",
          position: "relative",
          zIndex: 1,
        }}
      />
      {animatedBackground && <SurfaceOverlay variant={variant} />}
    </AbsoluteFill>
  );
};
