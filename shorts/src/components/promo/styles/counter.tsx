import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { FONT, COL, clamp, easeOut, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Scene: React.FC<SceneProps> = ({ data, durFrames, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  const m = c.join(" ").match(/\d[\d,]*/);

  // 숫자가 없으면 카운터는 부적합 → 가짜 숫자(구: 100까지 카운트업) 대신 청크를 타이포로 표시.
  // (마지막 청크 오렌지 강조, 나머지 흰색, 순차 등장)
  if (!m) {
    return (
      <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", alignItems: "center", padding: 90, gap: 12 }}>
        {c.map((t, i) => (
          <div
            key={i}
            style={{
              fontSize: i === c.length - 1 ? 120 : 64,
              fontWeight: 900,
              color: i === c.length - 1 ? variant.accent : variant.fg,
              textAlign: "center",
              lineHeight: 1.05,
              letterSpacing: i === c.length - 1 ? -2 : 0,
              wordBreak: "keep-all",
              opacity: clamp((frame - i * 4) / 10),
              transform: `translateY(${(1 - easeOut(clamp((frame - i * 4) / 10))) * 24}px)`,
            }}
          >
            {t}
          </div>
        ))}
      </AbsoluteFill>
    );
  }

  const target = parseInt(m[0].replace(/,/g, ""), 10);
  const p = clamp(frame / (durFrames * 0.7));
  const val = Math.round(target * easeOut(p));
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <div style={{ fontSize: 240, fontWeight: 900, color: variant.accent, letterSpacing: -4, lineHeight: 1 }}>{val.toLocaleString()}</div>
      <div style={{ fontSize: 70, fontWeight: 900, color: variant.fg, marginTop: 16, textAlign: "center", wordBreak: "keep-all" }}>{c[c.length - 1]}</div>
    </AbsoluteFill>
  );
};

export const counter: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
