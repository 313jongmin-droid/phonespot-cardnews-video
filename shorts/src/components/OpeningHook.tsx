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
  if (len <= 9) return 112;
  if (len <= 13) return 98;
  return 86;
};

// 강한 후킹용 오프닝: 평평한 검정 → 브랜드 다크 그라데이션 + 움직이는 주황 글로우,
// 채널 태그라인은 작은 주황 키커 pill, 헤드라인은 빠르게(0.3초 안에) 큼직하게 등장.
export const OpeningHook: React.FC<Props> = ({ line1, line2, durFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 빠른 등장(첫 프레임부터 키커·글로우 보임, 헤드라인은 ~6프레임에 안착)
  const kicker = interpolate(frame, [0, 4], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const barW = interpolate(frame, [3, 12], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const head = spring({ frame: frame - 2, fps, config: { damping: 12, stiffness: 260 } });
  const zoom = interpolate(frame, [0, durFrames], [1.0, 1.05]);
  // 글로우가 천천히 드리프트하며 살아있는 느낌
  const gx = interpolate(frame, [0, durFrames], [38, 62]);
  const gy = interpolate(frame, [0, durFrames], [34, 44]);

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(160deg, #1B0A03 0%, #0A0A0A 55%, #000000 100%)",
        justifyContent: "center",
        alignItems: "center",
        fontFamily:
          "'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
        transform: `scale(${zoom})`,
      }}
    >
      {/* 움직이는 주황 글로우 */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at ${gx}% ${gy}%, rgba(247,75,11,0.34), rgba(247,75,11,0.10) 26%, transparent 56%)`,
        }}
      />
      {/* 미세 그리드 */}
      <AbsoluteFill
        style={{
          backgroundImage:
            "linear-gradient(rgba(247,75,11,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(247,75,11,0.05) 1px, transparent 1px)",
          backgroundSize: "72px 72px",
          opacity: 0.7,
        }}
      />

      <div style={{ textAlign: "center", padding: "0 64px", position: "relative" }}>
        {/* 키커 pill (채널 태그라인) */}
        <div
          style={{
            display: "inline-block",
            background: "#F74B0B",
            color: "#FFFFFF",
            fontSize: 30,
            fontWeight: 800,
            letterSpacing: 0.5,
            padding: "10px 24px",
            borderRadius: 100,
            marginBottom: 30,
            opacity: kicker,
            transform: `translateY(${(1 - kicker) * -16}px)`,
          }}
        >
          {line1}
        </div>

        {/* 헤드라인 (빠르고 큼직하게) */}
        <div
          style={{
            fontSize: line2Size(line2),
            fontWeight: 900,
            color: "#FFFFFF",
            letterSpacing: -1,
            lineHeight: 1.14,
            wordBreak: "keep-all",
            overflowWrap: "break-word",
            opacity: Math.min(1, head * 1.4),
            transform: `translateY(${(1 - head) * 26}px) scale(${0.86 + head * 0.14})`,
            textShadow: "0 6px 30px rgba(0,0,0,0.5)",
          }}
        >
          {line2}
        </div>

        {/* 강조 바 */}
        <div
          style={{
            width: `${barW}%`,
            height: 9,
            backgroundColor: "#F74B0B",
            margin: "30px auto 0",
            borderRadius: 5,
            maxWidth: 520,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
