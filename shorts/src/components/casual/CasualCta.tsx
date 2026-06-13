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

interface CtaData {
  kakao?: string;
  location?: string;
  litt?: string;
  caption_chunks?: string[];
  caption_body?: string[] | string;
  headline_lines?: Array<{ text?: string } | string>;
}

interface Props {
  data: CtaData;
  audioKey: string;
  durFrames: number;
}

// 닫기 CTA = 일러스트 대신 디자인 카드(오프닝 후킹과 같은 결: 다크+주황 글로우+키커).
// "휴대폰 구매할 땐? → 지원금부터 무료로 조회" + 폰스팟 광교점 연락처.
export const CasualCta: React.FC<Props> = ({ data, audioKey, durFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const chunks = (data.caption_chunks || []).filter(Boolean);
  const hook = (chunks[0] || "휴대폰 구매할 땐?").trim();
  const punch = (chunks.slice(1).join(" ") || "지원금부터 무료로 조회").trim();
  const kakao = data.kakao || "@폰스팟광교점";
  const location = data.location || "광교호수공원 B1-47";
  const litt = data.litt || "litt.ly/phonespot";

  const kicker = interpolate(frame, [0, 5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const head = spring({ frame: frame - 3, fps, config: { damping: 13, stiffness: 240 } });
  const punchOp = interpolate(frame, [10, 18], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const cardOp = interpolate(frame, [16, 26], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const zoom = interpolate(frame, [0, durFrames], [1.0, 1.04]);
  const gx = interpolate(frame, [0, durFrames], [40, 60]);

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
      <Audio src={staticFile(`audio/${audioKey}.mp3`)} volume={1} />

      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at ${gx}% 38%, rgba(247,75,11,0.32), rgba(247,75,11,0.10) 26%, transparent 56%)`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage:
            "linear-gradient(rgba(247,75,11,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(247,75,11,0.05) 1px, transparent 1px)",
          backgroundSize: "72px 72px",
          opacity: 0.7,
        }}
      />

      <div style={{ textAlign: "center", padding: "0 64px", position: "relative", width: "100%" }}>
        {/* 키커 */}
        <div
          style={{
            display: "inline-block",
            background: "#F74B0B",
            color: "#FFFFFF",
            fontSize: 30,
            fontWeight: 800,
            padding: "10px 24px",
            borderRadius: 100,
            marginBottom: 28,
            opacity: kicker,
            transform: `translateY(${(1 - kicker) * -16}px)`,
          }}
        >
          {"폰스팟 광교점"}
        </div>

        {/* 후킹 */}
        <div
          style={{
            fontSize: 96,
            fontWeight: 900,
            color: "#FFFFFF",
            letterSpacing: -1.5,
            lineHeight: 1.12,
            wordBreak: "keep-all",
            opacity: Math.min(1, head * 1.4),
            transform: `translateY(${(1 - head) * 26}px) scale(${0.88 + head * 0.12})`,
            textShadow: "0 6px 30px rgba(0,0,0,0.5)",
          }}
        >
          {hook}
        </div>

        {/* 펀치라인(주황) */}
        <div
          style={{
            fontSize: 66,
            fontWeight: 900,
            color: "#FF7A3C",
            letterSpacing: -1,
            lineHeight: 1.16,
            wordBreak: "keep-all",
            marginTop: 18,
            opacity: punchOp,
          }}
        >
          {punch}
        </div>

        {/* 연락처 카드 */}
        <div
          style={{
            marginTop: 52,
            display: "inline-block",
            background: "rgba(255,255,255,0.06)",
            border: "1.5px solid rgba(247,75,11,0.55)",
            borderRadius: 22,
            padding: "26px 44px",
            opacity: cardOp,
            transform: `translateY(${(1 - cardOp) * 18}px)`,
          }}
        >
          <div style={{ fontSize: 52, fontWeight: 900, color: "#FFFFFF", letterSpacing: -0.5 }}>{kakao}</div>
          <div style={{ fontSize: 34, fontWeight: 700, color: "#FFE6D8", marginTop: 8 }}>{location}</div>
          <div style={{ fontSize: 30, fontWeight: 600, color: "#FFB089", marginTop: 4 }}>{litt}</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
