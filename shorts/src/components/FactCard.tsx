import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { NewsBackground } from "./NewsBackground";
import { NewsHeadlineOverlay } from "./NewsHeadlineOverlay";
import { StaticSubtitle } from "./StaticSubtitle";
import { StatBlock } from "./StatBlock";
import { Timeline } from "./dataviz/Timeline";
import { SpecGrid } from "./dataviz/SpecGrid";
import { CameraSpec } from "./dataviz/CameraSpec";
import { ComparisonBar } from "./dataviz/ComparisonBar";
import { FactSheet } from "./dataviz/FactSheet";

interface FactData {
  id: string;
  topic?: string;
  headline_lines: { text: string; accent?: boolean }[];
  meta: string;
  caption_lines: string[];
  caption_emphasis?: string[];
  stat: { label: string; value: string; note?: string };
  background_image: string;
  viz?: any;
}

interface Props {
  data: FactData;
  index: number;
  total: number;
  channelName: string;
  durFrames: number;
}

const renderViz = (viz: any, stat: any) => {
  if (!viz || viz.type === "stat")
    return <StatBlock label={stat.label} value={stat.value} note={stat.note} />;
  switch (viz.type) {
    case "timeline": return <Timeline points={viz.points} />;
    case "specgrid": return <SpecGrid items={viz.items} />;
    case "cameraspec": return <CameraSpec lenses={viz.lenses} />;
    case "comparison": return <ComparisonBar items={viz.items} title={viz.title || "COMPARE"} />;
    case "factsheet": return <FactSheet title={viz.title} rows={viz.rows} />;
    default: return <StatBlock label={stat.label} value={stat.value} note={stat.note} />;
  }
};

export const FactCard: React.FC<Props> = ({ data, index, total, channelName, durFrames }) => {
  return (
    <AbsoluteFill>
      <NewsBackground
        image={data.background_image}
        durFrames={durFrames}
        zoomFrom={1.06}
        zoomTo={1.0}
      />
      <Audio src={staticFile(`audio/fact_${index + 1}.mp3`)} />
      <NewsHeadlineOverlay
        topic={data.topic || "스펙"}
        channelName={channelName}
        lines={data.headline_lines}
        meta={data.meta}
      />
      {renderViz(data.viz, data.stat)}
      <StaticSubtitle
        lines={data.caption_lines}
        emphasisWords={data.caption_emphasis}
        durFrames={durFrames}
      />
    </AbsoluteFill>
  );
};
