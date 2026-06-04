import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, staticFile, useVideoConfig } from "remotion";
import { getStyle, sfxForStyle } from "./styles/registry";
import { variantFor } from "./styles/shared";

// 디스패처: 나레이션 없이 효과음+음악 기반. 섹션별 스타일/효과음 디렉팅.
// 타이밍은 고정 길이(sequenceSeconds, Root.calcPromo에서 산출). 음악은 music=true일 때 script.music_src 재생.
// music_start(초)가 있으면 곡의 그 지점부터 사용(파일명 끝 __NN 로 지정).
export interface PromoShortProps {
  script: any;
  sequenceSeconds: number[];
  introSec: number;
  outroSec: number;
  openingSec: number;
  track: string;
  promoStyle: string;
  styleMap?: Record<string, string>;
  sfx?: boolean;
  music?: boolean;
}

export const PromoShort: React.FC<PromoShortProps> = ({
  script,
  sequenceSeconds,
  outroSec,
  openingSec,
  promoStyle,
  styleMap,
  sfx = true,
  music = false,
}) => {
  const { fps } = useVideoConfig();
  const pickId = (override: string | undefined, key: string): string =>
    override || (styleMap && styleMap[key]) || promoStyle;
  const pickStyle = (override: string | undefined, key: string) =>
    getStyle(pickId(override, key));
  // 효과음 = 그 섹션 스타일(모션)에 맞춰. data.sfx로 직접 지정 시 그게 최우선.
  const sfxOf = (data: any, key: string, isCta: boolean): string =>
    (data && data.sfx) ? data.sfx : sfxForStyle(pickId(data && data.style, key), isCta);

  let cursor = 0;
  const openingFrames = Math.ceil(openingSec * fps);
  const openingStart = cursor;
  cursor += openingFrames;

  const sections = [
    { key: "hook", data: script.hook },
    ...script.facts.map((f: any, i: number) => ({ key: `fact_${i + 1}`, data: f })),
    { key: "cta", data: script.cta },
  ];
  const spans = sections.map((s, i) => {
    const dur = Math.ceil((sequenceSeconds[i] ?? 2.4) * fps);
    const start = cursor;
    cursor += dur;
    return { ...s, start, dur, index: i };
  });

  const outroFrames = Math.ceil(outroSec * fps);
  const outroStart = cursor;
  const totalFrames = outroStart + outroFrames;

  const O = pickStyle(script.opening && script.opening.style, "open");
  const Ou = pickStyle(undefined, "out");

  const sfxAt = (start: number, name: string, dur: number) =>
    sfx && name && name !== "none" ? (
      <Sequence key={`sfx-${start}`} from={start} durationInFrames={dur}>
        <Audio src={staticFile(`sfx/${name}.mp3`)} volume={0.8} />
      </Sequence>
    ) : null;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      {music !== false && script.music_src ? (
        <Sequence from={0} durationInFrames={totalFrames}>
          <Audio
            src={staticFile(script.music_src)}
            trimBefore={Math.round((script.music_start || 0) * fps)}
            volume={(f) =>
              interpolate(f, [0, 8, totalFrames - 26, totalFrames - 1], [0, 0.5, 0.5, 0], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })
            }
          />
        </Sequence>
      ) : null}

      <Sequence from={openingStart} durationInFrames={openingFrames}>
        <O.Opening line1={script.opening.line1} line2={script.opening.line2} durFrames={openingFrames} />
      </Sequence>

      {spans.map((sp) => {
        const isCta = sp.key === "cta";
        const Sc = pickStyle(sp.data && sp.data.style, sp.key);
        return (
          <Sequence key={sp.key} from={sp.start} durationInFrames={sp.dur}>
            <Sc.Scene
              data={sp.data}
              durFrames={sp.dur}
              variant={variantFor(sp.index)}
              isCta={isCta}
              ctaInfo={
                isCta
                  ? { kakao: script.cta.kakao, litt: script.cta.litt, location: script.cta.location }
                  : undefined
              }
            />
          </Sequence>
        );
      })}

      <Sequence from={outroStart} durationInFrames={outroFrames}>
        <Ou.Outro durFrames={outroFrames} />
      </Sequence>

      {sfxAt(openingStart, sfxOf(script.opening, "open", false), 18)}
      {spans.map((sp) => sfxAt(sp.start, sfxOf(sp.data, sp.key, sp.key === "cta"), sp.key === "cta" ? 40 : 18))}

      <AbsoluteFill style={{ background: "radial-gradient(125% 80% at 50% 40%, rgba(0,0,0,0) 42%, rgba(0,0,0,0.45) 100%)", pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
