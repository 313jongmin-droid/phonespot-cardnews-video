import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { FONT, COL, clamp, easeOut, chunksOf, CtaBlock, BasicOpening, BasicOutro, PromoStyle, SceneProps } from "./shared";

const Icon: React.FC<{ name: string; color: string }> = ({ name, color }) => {
  const common = { width: 300, height: 300, viewBox: "0 0 100 100", fill: "none", stroke: color, strokeWidth: 7, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  if (name === "phone") return (<svg {...common}><rect x="32" y="12" width="36" height="76" rx="8" /><line x1="46" y1="78" x2="54" y2="78" /></svg>);
  if (name === "tag") return (<svg {...common}><path d="M52 14 H84 V46 L50 80 18 48 Z" /><circle cx="72" cy="28" r="5" /></svg>);
  if (name === "check") return (<svg {...common}><circle cx="50" cy="50" r="36" /><path d="M34 52 L46 64 68 38" /></svg>);
  return (<svg {...common}><path d="M50 14 L58 42 86 50 58 58 50 86 42 58 14 50 42 42 Z" /></svg>);
};

const Scene: React.FC<SceneProps> = ({ data, variant, isCta, ctaInfo }) => {
  const frame = useCurrentFrame();
  if (isCta) return <CtaBlock data={data} ctaInfo={ctaInfo} />;
  const c = chunksOf(data);
  const joined = c.join(" ");
  const pick = /개통|폰|휴대/.test(joined) ? "phone" : /가격|조회|정찰|시세/.test(joined) ? "tag" : /비교|확인|숨김|투명/.test(joined) ? "check" : "spark";
  const a = clamp(frame / 6);
  const sc = 0.7 + 0.3 * easeOut(frame / 8);
  return (
    <AbsoluteFill style={{ backgroundColor: variant.bg, fontFamily: FONT, justifyContent: "center", alignItems: "center", padding: 90 }}>
      <div style={{ transform: `scale(${sc})`, opacity: a, marginBottom: 50 }}><Icon name={pick} color={variant.accent} /></div>
      <div style={{ fontSize: 104, fontWeight: 900, color: variant.fg, textAlign: "center", opacity: clamp((frame - 6) / 6), wordBreak: "keep-all", lineHeight: 1.1 }}>{c[c.length - 1]}</div>
    </AbsoluteFill>
  );
};
export const pictogram: PromoStyle = { Opening: BasicOpening, Scene, Outro: BasicOutro };
