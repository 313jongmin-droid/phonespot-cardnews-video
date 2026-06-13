import React from "react";
import { Composition, staticFile } from "remotion";
import { getAudioDurationInSeconds } from "@remotion/media-utils";
import { NewsShort } from "./Composition";
import { CoverShort } from "./Cover";
import { PromoShort } from "./components/promo/PromoShort";
import { PROMO_STYLES, PROMO_PRESETS } from "./components/promo/styles/registry";
import script from "../public/shorts_script.json";
import "./fonts";

const FPS = 30;
const GAP_SEC = 0.05;
const FALLBACK_SEC = 4.0;
const INTRO_SEC = 0;
const OPENING_SEC = 1.1;
const OUTRO_SEC = 1.2;
const PROMO_SEC = 2.4;   // 섹션 기본 길이(초) — 나레이션 없으니 고정
const PROMO_CTA = 3.0;   // CTA는 조금 길게

const audioPath = (key: string) => `audio/${key}.mp3`;
const tryDuration = async (key: string): Promise<number> => {
  try {
    return await getAudioDurationInSeconds(staticFile(audioPath(key)));
  } catch {
    return FALLBACK_SEC;
  }
};

const sequenceKeys = [
  "hook",
  ...script.facts.map((_: any, i: number) => `fact_${i + 1}`),
  "cta",
];

// casual/newsroom: 나레이션 mp3 길이 기반
const calc = async () => {
  const seconds = await Promise.all(
    sequenceKeys.map(async (k) => (await tryDuration(k)) + GAP_SEC)
  );
  const total = OPENING_SEC + INTRO_SEC + seconds.reduce((a, b) => a + b, 0) + OUTRO_SEC;
  return { durationInFrames: Math.ceil(total * FPS), seconds };
};

// promo: 나레이션 없음 → 섹션별 고정 길이(script.<section>.dur 로 개별 조정 가능)
const promoSeconds = (): number[] => {
  const arr: number[] = [script.hook && (script.hook as any).dur ? (script.hook as any).dur : PROMO_SEC];
  script.facts.forEach((f: any) => arr.push(f.dur ? f.dur : PROMO_SEC));
  arr.push((script.cta as any).dur ? (script.cta as any).dur : PROMO_CTA);
  return arr.map((s) => s + GAP_SEC);
};
const calcPromo = async () => {
  const seconds = promoSeconds();
  const total = OPENING_SEC + INTRO_SEC + seconds.reduce((a, b) => a + b, 0) + OUTRO_SEC;
  return { durationInFrames: Math.ceil(total * FPS), seconds };
};

export const RemotionRoot: React.FC = () => {
  const fallbackFrames = Math.ceil(
    (OPENING_SEC + INTRO_SEC + OUTRO_SEC + sequenceKeys.length * (FALLBACK_SEC + GAP_SEC)) * FPS
  );
  const fallbackSeconds = sequenceKeys.map(() => FALLBACK_SEC + GAP_SEC);
  const promoFallbackSeconds = promoSeconds();
  const promoFallbackFrames = Math.ceil(
    (OPENING_SEC + INTRO_SEC + OUTRO_SEC + promoFallbackSeconds.reduce((a, b) => a + b, 0)) * FPS
  );

  const promoComp = (id: string, extra: Record<string, any>) => (
    <Composition
      key={id}
      id={id}
      component={PromoShort as any}
      durationInFrames={promoFallbackFrames}
      fps={FPS}
      width={1080}
      height={1920}
      defaultProps={{
        script: script as any,
        sequenceSeconds: promoFallbackSeconds,
        introSec: INTRO_SEC,
        outroSec: OUTRO_SEC,
        openingSec: OPENING_SEC,
        track: "promo",
        sfx: true,
        music: true,
        ...extra,
      }}
      calculateMetadata={async ({ defaultProps }) => {
        const { durationInFrames, seconds } = await calcPromo();
        return { durationInFrames, props: { ...defaultProps, sequenceSeconds: seconds } };
      }}
    />
  );

  return (
    <>
      <Composition
        id="Cover"
        component={CoverShort as any}
        durationInFrames={1}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{ script: script as any }}
      />
      <Composition
        id="NewsroomShort"
        component={NewsShort as any}
        durationInFrames={fallbackFrames}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          script: script as any,
          sequenceSeconds: fallbackSeconds,
          introSec: INTRO_SEC,
          outroSec: OUTRO_SEC,
          openingSec: OPENING_SEC,
          track: "newsroom",
        }}
        calculateMetadata={async ({ defaultProps }) => {
          const { durationInFrames, seconds } = await calc();
          return { durationInFrames, props: { ...defaultProps, sequenceSeconds: seconds } };
        }}
      />
      <Composition
        id="CasualShort"
        component={NewsShort as any}
        durationInFrames={fallbackFrames}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          script: script as any,
          sequenceSeconds: fallbackSeconds,
          introSec: INTRO_SEC,
          outroSec: OUTRO_SEC,
          openingSec: OPENING_SEC,
          track: "casual",
        }}
        calculateMetadata={async ({ defaultProps }) => {
          const { durationInFrames, seconds } = await calc();
          return { durationInFrames, props: { ...defaultProps, sequenceSeconds: seconds } };
        }}
      />
      {PROMO_STYLES.map((s) => promoComp(`Promo-${s.id}`, { promoStyle: s.id }))}
      {Object.entries(PROMO_PRESETS).map(([name, map]) =>
        promoComp(`Promo-${name}`, { promoStyle: "kinetic", styleMap: map })
      )}
    </>
  );
};
