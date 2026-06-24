import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// 배너광고 트랙 - 스텝 스크롤 모드 (2026-06-19). casual 무수정.
// 섹션 이미지를 세로로 쌓고, 섹션마다 스크롤이 위로 올라가 멈춰(그 섹션 TTS 동안) 다음 섹션으로.
// CTA = build_banner 가 _cta.png 를 banners 끝에 자동첨부.

const PRETENDARD =
  "'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif";
const SECTION_H = 1080;
const SCROLL_SEC = 0.55;

interface Banner {
  image: string;
  audioKey: string;
  caption?: string;
}
interface BannerScript {
  banners?: Banner[];
  captionsOn?: boolean;
  bgm?: string;
  bgmVol?: number;
}
interface Props {
  script: BannerScript;
  sequenceSeconds: number[];
  captionsOn?: boolean;
}

function imgSrc(image: string): string {
  if (!image) return "";
  if (image.indexOf("/") >= 0) return staticFile("assets/" + image);
  return staticFile("assets/banners/" + image);
}

export const BannerAdShort: React.FC<Props> = ({ script, sequenceSeconds, captionsOn }) => {
  const { fps, height } = useVideoConfig();
  const frame = useCurrentFrame();
  const banners = (script.banners || []).filter((b) => b && b.image);
  const capOn = captionsOn != null ? captionsOn : script.captionsOn === true;
  const n = banners.length;

  const defFrames = Math.round(3 * fps);
  const frames = banners.map((_, i) =>
    sequenceSeconds && sequenceSeconds[i] ? Math.round(sequenceSeconds[i] * fps) : defFrames
  );
  const starts: number[] = [];
  let acc = 0;
  for (let i = 0; i < frames.length; i++) {
    starts.push(acc);
    acc += frames[i];
  }

  const totalStack = n * SECTION_H;
  const maxScroll = Math.max(0, totalStack - height);
  const targetY = (i: number) =>
    Math.min(maxScroll, Math.max(0, i * SECTION_H - (height - SECTION_H) / 2));

  let active = 0;
  for (let i = 0; i < n; i++) {
    if (frame >= starts[i]) active = i;
  }
  const localF = frame - (starts.length ? starts[active] : 0);
  const fromY = active > 0 ? targetY(active - 1) : targetY(0);
  const toY = targetY(active);
  const scrollY = interpolate(localF, [0, Math.round(SCROLL_SEC * fps)], [fromY, toY], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const activeCaption = banners[active] ? banners[active].caption : "";

  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: 1080,
          transform: "translateY(" + -scrollY + "px)",
          willChange: "transform",
        }}
      >
        {banners.map((b, i) => (
          <div
            key={"s" + i}
            style={{ width: 1080, height: SECTION_H, overflow: "hidden", backgroundColor: "#000000" }}
          >
            <Img src={imgSrc(b.image)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          </div>
        ))}
      </div>

      {script.bgm ? (
        <Audio src={staticFile(script.bgm)} volume={script.bgmVol != null ? script.bgmVol : 0.6} loop />
      ) : null}

      {capOn && activeCaption ? (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 140,
            textAlign: "center",
            padding: "0 48px",
            fontFamily: PRETENDARD,
            fontSize: 54,
            fontWeight: 900,
            color: "#FFFFFF",
            lineHeight: 1.22,
            wordBreak: "keep-all",
            textShadow: "0 4px 20px rgba(0,0,0,0.8)",
          }}
        >
          {activeCaption}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
