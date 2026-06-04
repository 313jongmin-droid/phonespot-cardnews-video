import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { NewsBackground } from "./NewsBackground";
import { NewsHeadlineOverlay } from "./NewsHeadlineOverlay";
import { StaticSubtitle } from "./StaticSubtitle";

interface Props {
  data: {
    topic?: string;
    headline_lines: { text: string; accent?: boolean }[];
    meta: string;
    caption_lines: string[];
    caption_emphasis?: string[];
    background_image: string;
    background_video?: string;
  };
  channelName: string;
  durFrames: number;
}

export const HookCard: React.FC<Props> = ({ data, channelName, durFrames }) => {
  return (
    <AbsoluteFill>
      <NewsBackground
        image={data.background_image}
        video={data.background_video}
        durFrames={durFrames}
        zoomFrom={1.0}
        zoomTo={1.1}
      />
      <Audio src={staticFile("audio/hook.mp3")} />
      <NewsHeadlineOverlay
        topic={data.topic || "갤럭시"}
        channelName={channelName}
        lines={data.headline_lines}
        meta={data.meta}
      />
      <StaticSubtitle
        lines={data.caption_lines}
        emphasisWords={data.caption_emphasis}
        durFrames={durFrames}
      />
    </AbsoluteFill>
  );
};
