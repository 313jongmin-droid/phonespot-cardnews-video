import React from "react";
import { AbsoluteFill, Sequence, useVideoConfig } from "remotion";
import { ChannelOutro } from "./components/ChannelOutro";
import { OpeningHook } from "./components/OpeningHook";
import { HookCard } from "./components/HookCard";
import { FactCard } from "./components/FactCard";
import { CtaCard } from "./components/CtaCard";
import { CasualCard } from "./components/casual/CasualCard";
import { CasualCta } from "./components/casual/CasualCta";
import { NoiseOverlay } from "./components/NoiseOverlay";

export interface Script {
  slug: string;
  title_short: string;
  video_title: string;
  channel_name: string;
  channel_tagline: string;
  sources: string;
  publication_date: string;
  opening: { line1: string; line2: string };
  hook: any;
  facts: any[];
  cta: any;
}

export interface NewsShortProps {
  script: Script;
  sequenceSeconds: number[];
  introSec: number;
  outroSec: number;
  openingSec: number;
  track: "newsroom" | "casual";
}

export const NewsShort: React.FC<NewsShortProps> = ({
  script,
  sequenceSeconds,
  introSec,
  outroSec,
  openingSec,
  track,
}) => {
  const { fps } = useVideoConfig();
  const isCasual = track === "casual";
  const introFrames = Math.ceil(introSec * fps);
  const outroFrames = Math.ceil(outroSec * fps);

  let cursor = 0;
  const openingFrames = Math.ceil(openingSec * fps);
  const openingStart = cursor;
  cursor += openingFrames;

  const introStart = cursor;
  cursor += introFrames;

  const hookFrames = Math.ceil(sequenceSeconds[0] * fps);
  const hookStart = cursor;
  cursor += hookFrames;

  const factStarts: number[] = [];
  const factFrames: number[] = [];
  script.facts.forEach((_, i) => {
    const frames = Math.ceil(sequenceSeconds[i + 1] * fps);
    factStarts.push(cursor);
    factFrames.push(frames);
    cursor += frames;
  });

  const ctaFrames = Math.ceil(sequenceSeconds[sequenceSeconds.length - 1] * fps);
  const ctaStart = cursor;
  cursor += ctaFrames;
  const outroStart = cursor;

  const ch = script.channel_name;
  const chCasual = "\uD3F0\uC2A4\uD31F IT";

  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      <Sequence from={openingStart} durationInFrames={openingFrames}>
        <OpeningHook line1={script.opening.line1} line2={script.opening.line2} durFrames={openingFrames} />
      </Sequence>

      {introFrames > 0 && (
        <Sequence from={introStart} durationInFrames={introFrames}>
          <AbsoluteFill style={{ backgroundColor: "#000" }} />
        </Sequence>
      )}

      <Sequence from={hookStart} durationInFrames={hookFrames}>
        {isCasual ? (
          <CasualCard
            data={script.hook}
            channelName={chCasual}
            videoTitle={script.video_title}
            audioKey="hook"
            type="hook"
            durFrames={hookFrames}
          />
        ) : (
          <HookCard data={script.hook} channelName={ch} durFrames={hookFrames} />
        )}
      </Sequence>

      {script.facts.map((fact, i) => (
        <Sequence key={fact.id || i} from={factStarts[i]} durationInFrames={factFrames[i]}>
          {isCasual ? (
            <CasualCard
              data={fact}
              channelName={chCasual}
              videoTitle={script.video_title}
              audioKey={`fact_${i + 1}`}
              type="fact"
              durFrames={factFrames[i]}
            />
          ) : (
            <FactCard
              data={fact}
              index={i}
              total={script.facts.length}
              channelName={ch}
              durFrames={factFrames[i]}
            />
          )}
        </Sequence>
      ))}

      <Sequence from={ctaStart} durationInFrames={ctaFrames}>
        {isCasual ? (
          <CasualCta data={script.cta} audioKey="cta" durFrames={ctaFrames} />
        ) : (
          <CtaCard data={script.cta} channelName={ch} durFrames={ctaFrames} />
        )}
      </Sequence>

      <Sequence from={outroStart} durationInFrames={outroFrames}>
        <ChannelOutro channelName={isCasual ? chCasual : ch} durFrames={outroFrames} />
      </Sequence>

      {!isCasual && <NoiseOverlay opacity={0.04} />}
    </AbsoluteFill>
  );
};