import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { CasualCta } from "../casual/CasualCta";

// 배너광고 트랙 (신규, 2026-06-19) — 카드뉴스 엔진 부품 재사용, casual 무수정.
// 입력: 완성 배너 이미지 N장 + 배너별 TTS + (옵션)자막 + CTA. 풀블리드 + 켄번스.
// 데이터 = public/shorts_script.json 의 banner 모드 필드:
//   { banners: [{ image, audioKey, caption? }], cta: <CasualCta data + audioKey>, captionsOn?, format? }

interface Banner {
  image: string;
  audioKey: string;
  caption?: string;
}
interface BannerScript {
  banners?: Banner[];
  cta?: any;
  captionsOn?: boolean;
}
interface Props {
  script: BannerScript;
  sequenceSeconds: number[]; // [banner1, banner2, ..., cta]
  captionsOn?: boolean;
}

// 배너 이미지 경로: "banners/이름.png" 또는 경로 포함이면 assets/<value>, 아니면 assets/banners/<value>
function imgSrc(image: string): string {
  if (!image) return "";
  if (image.includes("/")) return staticFile(`assets/${image}`);
  return staticFile(`assets/banners/${image}`);
}

const BannerCell: React.FC<{ banner: Banner; durFrames: number; captionsOn: boolean }> = ({
  banner,
  durFrames,
  captionsOn,
}) => {
  const frame = useCurrentFrame();
  // 켄번스 살짝 줌 + 등장 페이드
  const scale = interpolate(frame, [0, durFrames], [1.0, 1.06], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const enter = interpolate(frame, [0, 7], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const src = imgSrc(banner.image);
  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      <Audio src={staticFile(`audio/${banner.audioKey}.mp3`)} volume={1} />
      {src ? (
        <Img
          src={src}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${scale})`,
            opacity: enter,
          }}
        />
      ) : null}
      {captionsOn && banner.caption ? (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 240,
            textAlign: "center",
            padding: "0 48px",
            fontFamily:
              "'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
            fontSize: 58,
            fontWeight: 900,
            color: "#FFFFFF",
            letterSpacing: -1,
            lineHeight: 1.22,
            wordBreak: "keep-all",
            textShadow: "0 4px 20px rgba(0,0,0,0.75)",
          }}
        >
          {banner.caption}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

export const BannerAdShort: React.FC<Props> = ({ script, sequenceSeconds, captionsOn }) => {
  const { fps } = useVideoConfig();
  const banners = script.banners || [];
  const capOn = captionsOn ?? script.captionsOn ?? false;
  const frames = (sequenceSeconds || []).map((s) => Math.round(s * fps));
  const defFrames = Math.round(3 * fps);

  let cursor = 0;
  const cells = banners.map((b, i) => {
    const from = cursor;
    const dur = frames[i] ?? defFrames;
    cursor += dur;
    return (
      <Sequence key={`b${i}`} from={from} durationInFrames={dur}>
        <BannerCell banner={b} durFrames={dur} captionsOn={capOn} />
      </Sequence>
    );
  });

  const ctaDur = frames[banners.length] ?? defFrames;
  const ctaKey = (script.cta && (script.cta as any).audioKey) || "cta";

  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      {cells}
      {script.cta ? (
        <Sequence from={cursor} durationInFrames={ctaDur}>
          <CasualCta data={script.cta} audioKey={ctaKey} durFrames={ctaDur} />
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};
