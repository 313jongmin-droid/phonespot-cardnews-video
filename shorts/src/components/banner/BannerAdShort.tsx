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

// 배너광고 트랙 (2026-06-19, 자동분기판). casual 무수정.
// 1장 = 풀스크린(블러배경 + 천천히 줌 + 하단 브랜드 CTA바).
// 2장+ = 세로 스텝 스크롤(상세페이지 느낌) + 블러배경. 검은 여백 없음.
// CTA = build_banner 가 _cta.png(유효 이미지일 때) 를 banners 끝에 자동첨부.

const PRETENDARD =
  "'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif";
const SECTION_H = 1080;
const SCROLL_SEC = 0.55;
const BRAND = "휴대폰성지 폰스팟";
const LINK = "litt.ly/phonespot";

interface Banner {
  image: string;
  audioKey: string;
  caption?: string;
}
interface BannerScript {
  banners?: Banner[];
  secPerBanner?: number;
  bgm?: string;
  bgmVol?: number;
}
interface Props {
  script: BannerScript;
  sequenceSeconds: number[];
}

function imgSrc(image: string): string {
  if (!image) return "";
  if (image.indexOf("/") >= 0) return staticFile("assets/" + image);
  return staticFile("assets/banners/" + image);
}

export const BannerAdShort: React.FC<Props> = ({ script, sequenceSeconds }) => {
  const { fps, width, height } = useVideoConfig();
  const frame = useCurrentFrame();
  const banners = (script.banners || []).filter((b) => b && b.image);
  const n = banners.length;

  const defFrames = Math.round((script.secPerBanner || 2.8) * fps);
  const frames = banners.map((_, i) =>
    sequenceSeconds && sequenceSeconds[i] ? Math.round(sequenceSeconds[i] * fps) : defFrames
  );
  const starts: number[] = [];
  let acc = 0;
  for (let i = 0; i < frames.length; i++) {
    starts.push(acc);
    acc += frames[i];
  }
  const totalFrames = acc || defFrames;

  let active = 0;
  for (let i = 0; i < n; i++) {
    if (frame >= starts[i]) active = i;
  }
  const bgImage = banners[active] ? banners[active].image : banners[0] ? banners[0].image : "";

  const blurBg = bgImage ? (
    <Img
      src={imgSrc(bgImage)}
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        objectFit: "cover",
        filter: "blur(48px) brightness(0.55) saturate(1.1)",
        transform: "scale(1.25)",
      }}
    />
  ) : null;

  const bgmEl = script.bgm ? (
    <Audio src={staticFile(script.bgm)} volume={script.bgmVol != null ? script.bgmVol : 0.6} loop />
  ) : null;

  // ── 풀스크린 단일 모드 ──
  if (n <= 1) {
    const zoom = interpolate(frame, [0, totalFrames], [1.0, 1.06], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return (
      <AbsoluteFill style={{ backgroundColor: "#0a0a0a" }}>
        {blurBg}
        {bgmEl}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Img
            src={imgSrc(bgImage)}
            style={{
              width: "100%",
              maxHeight: "100%",
              objectFit: "contain",
              transform: "scale(" + zoom + ")",
              filter: "drop-shadow(0 24px 60px rgba(0,0,0,0.45))",
            }}
          />
        </div>
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            height: 230,
            background: "linear-gradient(to top, rgba(0,0,0,0.88), rgba(0,0,0,0))",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "flex-end",
            paddingBottom: 70,
            fontFamily: PRETENDARD,
          }}
        >
          <div style={{ color: "#fff", fontSize: 52, fontWeight: 900, letterSpacing: "-1px" }}>
            {BRAND}
          </div>
          <div
            style={{
              marginTop: 16,
              padding: "14px 34px",
              borderRadius: 999,
              background: "#ff3b30",
              color: "#fff",
              fontSize: 38,
              fontWeight: 800,
            }}
          >
            지금 확인 → {LINK}
          </div>
        </div>
      </AbsoluteFill>
    );
  }

  // ── 멀티섹션 스크롤 모드 ──
  const totalStack = n * SECTION_H;
  const maxScroll = Math.max(0, totalStack - height);
  const targetY = (i: number) =>
    Math.min(maxScroll, Math.max(0, i * SECTION_H - (height - SECTION_H) / 2));
  const localF = frame - (starts.length ? starts[active] : 0);
  const fromY = active > 0 ? targetY(active - 1) : targetY(0);
  const toY = targetY(active);
  const scrollY = interpolate(localF, [0, Math.round(SCROLL_SEC * fps)], [fromY, toY], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0a" }}>
      {blurBg}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: width,
          transform: "translateY(" + -scrollY + "px)",
          willChange: "transform",
        }}
      >
        {banners.map((b, i) => (
          <div
            key={"s" + i}
            style={{ width: width, height: SECTION_H, overflow: "hidden" }}
          >
            <Img src={imgSrc(b.image)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          </div>
        ))}
      </div>
      {bgmEl}
    </AbsoluteFill>
  );
};
