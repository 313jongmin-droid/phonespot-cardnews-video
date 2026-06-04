import React from "react";
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";

interface Props {
  image?: string;
  video?: string;
  durFrames: number;
  zoomFrom?: number;
  zoomTo?: number;
}

// 풀스크린 배경.
// - video: 9:16로 제작되어 cover로 꽉 채움
// - image: 4:3 일러스트라 cover하면 상하 크롭 → 블러 확대본을 배경에 깔고
//   원본은 contain으로 얹어 잘림 없이 표시
export const NewsBackground: React.FC<Props> = ({
  image,
  video,
  durFrames,
  zoomFrom = 1.0,
  zoomTo = 1.08,
}) => {
  const frame = useCurrentFrame();
  const zoom = interpolate(frame, [0, durFrames], [zoomFrom, zoomTo]);

  return (
    <AbsoluteFill style={{ backgroundColor: "#0A0A0A", overflow: "hidden" }}>
      {video ? (
        <AbsoluteFill style={{ transform: `scale(${zoom})` }}>
          <OffthreadVideo
            src={staticFile(`assets/${video}`)}
            muted
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </AbsoluteFill>
      ) : image ? (
        <>
          {/* 블러 확대 배경 — 빈 공간 채움 */}
          <AbsoluteFill style={{ transform: `scale(${zoom * 1.2})` }}>
            <Img
              src={staticFile(`assets/${image}`)}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                filter: "blur(42px) brightness(0.9)",
              }}
            />
          </AbsoluteFill>
          {/* 원본 일러스트 — 잘림 없이 contain */}
          <AbsoluteFill
            style={{
              transform: `scale(${zoom})`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Img
              src={staticFile(`assets/${image}`)}
              style={{
                maxWidth: "100%",
                maxHeight: "100%",
                objectFit: "contain",
              }}
            />
          </AbsoluteFill>
        </>
      ) : null}

      {/* 상하단 그라데이션 — 헤드라인/자막 가독성 */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(10,10,10,0.52) 0%, rgba(10,10,10,0.12) 20%, rgba(10,10,10,0.0) 46%, rgba(10,10,10,0.0) 60%, rgba(10,10,10,0.28) 78%, rgba(10,10,10,0.66) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};
