import React from "react";
import { AbsoluteFill, Audio, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { CasualHeader } from "./CasualHeader";
import { CasualTitleBar } from "./CasualTitleBar";
import { CasualCaption } from "./CasualCaption";
import { Mascot } from "./Mascot";
import { PriceBar, Timeline, StatBig, Compare, Calendar, BankAccount } from "./Infographics";
import { Illust } from "./Illustrations";
import { PhonespotLogo } from "./PhonespotLogo";
import { chunkIndexFromList, getChunkWindow, getVisualWindow, repairListChunkBoundaries } from "./chunkUtil";

interface ChunkVisual {
  type: string;
  value: any;
}

interface CardData {
  id?: string;
  background_image: string;
  caption_chunks: string[];
  display_chunks?: string[];
  tts_chunk_weights?: number[];
  chunk_visuals?: ChunkVisual[];
  caption_emphasis?: string[];
  kakao?: string;
  location?: string;
  litt?: string;
}

interface Props {
  data: CardData;
  channelName: string;
  videoTitle: string;
  audioKey: string;
  type: "hook" | "fact" | "cta";
  durFrames: number;
}

const IMAGE_MOTION_PRESETS = [
  { scaleFrom: 1.0, scaleTo: 1.14, xFrom: -18, xTo: 18, yFrom: 6, yTo: -6 },
  { scaleFrom: 1.08, scaleTo: 1.08, xFrom: -42, xTo: 42, yFrom: 0, yTo: 0 },
  { scaleFrom: 1.08, scaleTo: 1.08, xFrom: 42, xTo: -42, yFrom: 0, yTo: 0 },
  { scaleFrom: 1.04, scaleTo: 1.16, xFrom: 0, xTo: 0, yFrom: 24, yTo: -24 },
  { scaleFrom: 1.16, scaleTo: 1.03, xFrom: -22, xTo: 22, yFrom: -18, yTo: 18 },
  { scaleFrom: 1.05, scaleTo: 1.15, xFrom: 34, xTo: -28, yFrom: 18, yTo: -14 },
];

const clampProgress = (frame: number, duration: number) =>
  interpolate(frame, [0, Math.max(1, duration - 1)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

const ImageVisual: React.FC<{
  filename: string;
  chunkFrame: number;
  chunkDurFrames: number;
  variant: number;
  motionEnabled: boolean;
}> = ({ filename, chunkFrame, chunkDurFrames, variant, motionEnabled }) => {
  const src = staticFile(`assets/${filename}`);

  // Motion is percentage-based over the visible chunk window:
  // long exposure = same total movement over more frames (slower),
  // short exposure = same total movement over fewer frames (faster).
  const progress = motionEnabled ? clampProgress(chunkFrame, chunkDurFrames) : 0;
  const preset = IMAGE_MOTION_PRESETS[Math.abs(variant) % IMAGE_MOTION_PRESETS.length];
  const ease = 1 - Math.pow(1 - progress, 2);
  const scale = motionEnabled ? interpolate(ease, [0, 1], [preset.scaleFrom, preset.scaleTo]) : 1;
  const panX = motionEnabled ? interpolate(ease, [0, 1], [preset.xFrom, preset.xTo]) : 0;
  const panY = motionEnabled ? interpolate(ease, [0, 1], [preset.yFrom, preset.yTo]) : 0;
  const bgScale = motionEnabled ? 1.1 + ease * 0.04 : 1.1;

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", overflow: "hidden", backgroundColor: "#FFF1EA" }}>
      <Img
        src={src}
        style={{
          position: "absolute",
          inset: -54,
          width: "calc(100% + 108px)",
          height: "calc(100% + 108px)",
          objectFit: "cover",
          filter: "blur(26px) saturate(1.1)",
          opacity: 0.5,
          transform: `scale(${bgScale}) translate(${panX * -0.32}px, ${panY * -0.32}px)`,
        }}
      />
      <Img
        src={src}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "contain",
          transform: `scale(${scale}) translate(${panX}px, ${panY}px)`,
          transformOrigin: "center center",
          willChange: motionEnabled ? "transform" : "auto",
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(180deg, rgba(255,241,234,0.04), rgba(255,255,255,0.00) 45%, rgba(255,241,234,0.08))",
          pointerEvents: "none",
        }}
      />
    </div>
  );
};

export const CasualCard: React.FC<Props> = ({
  data,
  channelName,
  videoTitle,
  audioKey,
  type,
  durFrames,
}) => {
  const frame = useCurrentFrame();
  const captionChunks = repairListChunkBoundaries(data.caption_chunks || []);
  const displayChunks = repairListChunkBoundaries(data.display_chunks || captionChunks);
  const chunkIdx = chunkIndexFromList(captionChunks, frame, durFrames, data.tts_chunk_weights);
  const chunkWindow = getChunkWindow(captionChunks, chunkIdx, durFrames, data.tts_chunk_weights);
  const visualWindow =
    type === "cta"
      ? { ...chunkWindow, visualIndex: chunkIdx }
      : getVisualWindow(captionChunks, frame, durFrames, data.tts_chunk_weights);
  const visualChunkFrame = Math.max(0, frame - visualWindow.start);
  const visualIdx = visualWindow.visualIndex;
  const visuals = data.chunk_visuals || [];
  const visualVariant = visualIdx + audioKey.split("").reduce((sum, ch) => sum + ch.charCodeAt(0), 0);

  const cv: ChunkVisual =
    visuals[visualIdx] ||
    visuals[visuals.length - 1] || {
      type: "image",
      value: data.background_image,
    };

  const imageMotionEnabled = type !== "cta" && cv.type === "image";

  const renderVisual = () => {
    switch (cv.type) {
      case "mascot":
        return <Mascot emotion={cv.value as any} />;
      case "pricebar":
        return <PriceBar data={cv.value} />;
      case "timeline":
        return <Timeline data={cv.value} />;
      case "stat":
        return <StatBig data={cv.value} />;
      case "compare":
        return <Compare data={cv.value} />;
      case "calendar":
        return <Calendar data={cv.value} />;
      case "bankaccount":
        return <BankAccount data={cv.value} />;
      case "illust":
        return <Illust variant={cv.value as string} animatedBackground={type !== "cta"} />;
      case "logo":
        return <PhonespotLogo filename={typeof cv.value === "string" ? cv.value : undefined} />;
      case "image":
      default:
        return (
          <ImageVisual
            filename={String(cv.value)}
            chunkFrame={visualChunkFrame}
            chunkDurFrames={visualWindow.duration}
            variant={visualVariant}
            motionEnabled={imageMotionEnabled}
          />
        );
    }
  };

  // Only moving source images get the tiny visual intro. Static assets should
  // stay static: illustrations, CTA image, mascot, logo, infographics.
  const visualOpacity = imageMotionEnabled
    ? interpolate(visualChunkFrame, [0, 5], [0.86, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;
  const visualScale = imageMotionEnabled
    ? interpolate(visualChunkFrame, [0, 5], [0.985, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;

  return (
    <AbsoluteFill style={{ backgroundColor: "#FFFFFF" }}>
      <Audio src={staticFile(`audio/${audioKey}.mp3`)} volume={1} />

      <CasualHeader channelName={channelName} />
      {/* 제목바는 첫(hook) 카드에만 — 모든 카드 반복 제거 + 본문 카드 비주얼 영역 확대.
          맥락은 오프닝 헤드라인 + 헤더 '폰스팟 IT' + 비주얼/자막으로 충분. */}
      {type === "hook" && <CasualTitleBar title={videoTitle} />}

      <div
        style={{
          flex: 1,
          position: "relative",
          backgroundColor: "#FFF1EA",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: visualOpacity,
            transform: `scale(${visualScale})`,
            transformOrigin: "center center",
            willChange: imageMotionEnabled ? "opacity, transform" : "auto",
          }}
        >
          {renderVisual()}
        </div>
      </div>

      {type === "cta" && data.kakao && (
        <div
          style={{
            backgroundColor: "#F74B0B",
            padding: "26px 40px",
            textAlign: "center",
            fontFamily: "'Pretendard', -apple-system, sans-serif",
          }}
        >
          <div style={{ fontSize: 28, fontWeight: 700, color: "#FFE6D8" }}>
            {"\uAD11\uAD50\uC810 \uD3F0\uC2A4\uD31F"}
          </div>
          <div
            style={{
              fontSize: 50,
              fontWeight: 900,
              color: "#FFFFFF",
              letterSpacing: 0,
              margin: "4px 0",
            }}
          >
            {data.kakao}
          </div>
          <div style={{ fontSize: 30, fontWeight: 700, color: "#FFFFFF", marginTop: 4 }}>
            {data.location}
          </div>
          <div style={{ fontSize: 26, fontWeight: 600, color: "#FFE6D8" }}>
            {data.litt}
          </div>
        </div>
      )}

      <CasualCaption
        chunks={captionChunks}
        displayChunks={displayChunks}
        emphasisWords={data.caption_emphasis}
        timingWeights={data.tts_chunk_weights}
        durFrames={durFrames}
      />
    </AbsoluteFill>
  );
};
