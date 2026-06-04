import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { NewsBackground } from "./NewsBackground";
import { NewsHeadlineOverlay } from "./NewsHeadlineOverlay";

interface CtaData {
  topic?: string;
  headline_lines: { text: string; accent?: boolean }[];
  meta: string;
  caption_lines: string[];
  kakao: string;
  location: string;
  litt: string;
  background_image: string;
}

interface Props {
  data: CtaData;
  channelName: string;
  durFrames: number;
}

export const CtaCard: React.FC<Props> = ({ data, channelName, durFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const boxEnter = spring({ frame: frame - 12, fps, config: { damping: 14, stiffness: 150 } });
  const line = (d: number) =>
    interpolate(frame, [d, d + 9], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      <NewsBackground
        image={data.background_image}
        durFrames={durFrames}
        zoomFrom={1.0}
        zoomTo={1.08}
      />
      <Audio src={staticFile("audio/cta.mp3")} />
      <NewsHeadlineOverlay
        topic={data.topic || "안내"}
        channelName={channelName}
        lines={data.headline_lines}
        meta={data.meta}
      />

      <div
        style={{
          position: "absolute",
          left: 48,
          right: 48,
          bottom: 110,
          padding: "44px 38px",
          backgroundColor: "rgba(247,75,11,0.95)",
          borderRadius: 18,
          textAlign: "center",
          fontFamily: "'Pretendard', -apple-system, sans-serif",
          opacity: boxEnter,
          transform: `scale(${0.9 + boxEnter * 0.1})`,
        }}
      >
        <div style={{ fontSize: 34, fontWeight: 600, color: "#FFE6D8", opacity: line(6) }}>
          광교점 폰스팟
        </div>
        <div
          style={{
            fontSize: 64,
            fontWeight: 900,
            color: "#FFFFFF",
            letterSpacing: "-0.03em",
            margin: "8px 0 24px",
            opacity: line(12),
          }}
        >
          {data.kakao}
        </div>
        <div style={{ fontSize: 34, fontWeight: 700, color: "#FFFFFF", opacity: line(20) }}>
          {data.location}
        </div>
        <div
          style={{
            fontSize: 28,
            fontWeight: 600,
            color: "#FFE6D8",
            marginTop: 8,
            opacity: line(28),
          }}
        >
          {data.litt}
        </div>
      </div>
    </AbsoluteFill>
  );
};
