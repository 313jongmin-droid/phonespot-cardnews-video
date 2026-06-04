import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface Props {
  channelName: string;
  durFrames: number;
}

export const ChannelOutro: React.FC<Props> = ({ channelName, durFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 셔터 클로즈 (시작에서 막대가 안쪽으로)
  const shutterEnd = 10;
  const shutterProgress = interpolate(frame, [0, shutterEnd], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // 로고 등장
  const logoSpring = spring({
    frame: frame - 6,
    fps,
    config: { damping: 11, stiffness: 200 },
  });

  // "구독" 버튼 클릭 펄스 (반복)
  const pulse = 1 + 0.06 * Math.sin(frame / 4);

  // 텍스트 라인별 등장
  const line1Op = interpolate(frame, [12, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const line2Op = interpolate(frame, [18, 26], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#0A0A0A",
        justifyContent: "center",
        alignItems: "center",
        fontFamily:
          "'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
        overflow: "hidden",
      }}
    >
      {/* 그리드 */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(247,75,11,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(247,75,11,0.04) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />

      <div style={{ textAlign: "center" }}>
        {/* 로고 */}
        <div
          style={{
            fontSize: 180,
            fontWeight: 900,
            letterSpacing: "-0.05em",
            color: "#F74B0B",
            lineHeight: 1,
            transform: `scale(${0.6 + logoSpring * 0.4})`,
          }}
        >
          {channelName}
        </div>

        {/* 구독 유도 박스 */}
        <div
          style={{
            marginTop: 60,
            display: "inline-block",
            padding: "20px 56px",
            backgroundColor: "#F74B0B",
            color: "#FFFFFF",
            fontSize: 56,
            fontWeight: 900,
            letterSpacing: "-0.02em",
            borderRadius: 14,
            transform: `scale(${pulse})`,
            opacity: line1Op,
            boxShadow: "0 0 0 4px rgba(247,75,11,0.25)",
          }}
        >
          구독 + 좋아요
        </div>

        <div
          style={{
            marginTop: 32,
            fontSize: 36,
            fontWeight: 600,
            color: "#FFFFFF",
            opacity: line2Op * 0.75,
            letterSpacing: "-0.01em",
          }}
        >
          매주 새 IT 뉴스 / 광교호수공원 B1-47
        </div>
      </div>

      {/* 셔터 클로즈 잔상 */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: `${shutterProgress * 50}%`,
          backgroundColor: "#0A0A0A",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: `${shutterProgress * 50}%`,
          backgroundColor: "#0A0A0A",
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
