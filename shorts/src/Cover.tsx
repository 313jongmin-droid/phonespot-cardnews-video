import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import type { Script } from "./Composition";

// 9:16 Reels/Shorts 커버(정지컷). renderStill 로 1프레임만 렌더한다.
// 데이터는 영상과 동일한 public/shorts_script.json 의 hook 을 사용한다.
// - 헤드라인: hook.headline_lines ([{text},{text,accent}]) → 없으면 video_title 분할
// - 비주얼: hook.chunk_visuals 에서 첫 illust/image → background_image → facts 폴백
//   illust  value -> assets/illustrations/<value>.png
//   image   value -> assets/<value>   (예: "1.png")

const BRAND = "#F74B0B";
const PEACH = "#FFF1EA";
const INK = "#1A1A1A";
const FONT = "'Pretendard', -apple-system, 'Apple SD Gothic Neo', sans-serif";

type Visual = { type: string; value: any };

function visualSrc(v: Visual | undefined): string | null {
  if (!v) return null;
  if (v.type === "illust" && typeof v.value === "string") {
    return staticFile(`assets/illustrations/${v.value}.png`);
  }
  if (v.type === "image" && typeof v.value === "string" && v.value) {
    return staticFile(`assets/${v.value}`);
  }
  return null;
}

function pickHeroSrc(script: Script): string | null {
  const hook: any = script.hook || {};
  const sections: any[] = [hook, ...(script.facts || [])];
  // 실사 사진/카드이미지(type image, photos/ 등) 우선 → 없으면 일러스트(2026-06-19, 싸당 벤치마크)
  for (const wantImage of [true, false]) {
    for (const sec of sections) {
      for (const v of (sec.chunk_visuals || []) as Visual[]) {
        if (wantImage && v.type !== "image") continue;
        if (!wantImage && v.type !== "illust") continue;
        const src = visualSrc(v);
        if (src) return src;
      }
    }
  }
  // 폴백: background_image (카드이미지)
  const bg = hook.background_image;
  if (typeof bg === "string" && bg) return staticFile(`assets/${bg}`);
  return null;
}

function pickHeadline(script: Script): { l1: string; l2: string } {
  const hl: any[] = (script.hook && (script.hook as any).headline_lines) || [];
  const l1 = (hl[0] && String(hl[0].text || "").trim()) || "";
  const l2 = (hl[1] && String(hl[1].text || "").trim()) || "";
  if (l1 || l2) return { l1, l2 };
  // 폴백: video_title 를 두 줄로
  const t = String(script.video_title || script.title_short || "").trim();
  if (!t) return { l1: "", l2: "" };
  const words = t.split(/\s+/);
  if (words.length < 2) return { l1: t, l2: "" };
  const mid = Math.ceil(words.length / 2);
  return { l1: words.slice(0, mid).join(" "), l2: words.slice(mid).join(" ") };
}

export const CoverShort: React.FC<{ script: Script }> = ({ script }) => {
  const hero = pickHeroSrc(script);
  const { l1, l2 } = pickHeadline(script);

  return (
    <AbsoluteFill style={{ backgroundColor: "#FFFFFF", fontFamily: FONT }}>
      {/* 상단 브랜드 배지 */}
      <div
        style={{
          position: "absolute",
          top: 64,
          left: 64,
          display: "flex",
          alignItems: "center",
          gap: 16,
        }}
      >
        <div
          style={{
            backgroundColor: BRAND,
            color: "#FFFFFF",
            fontWeight: 900,
            fontSize: 40,
            letterSpacing: -1,
            padding: "12px 28px",
            borderRadius: 18,
          }}
        >
          {"폰스팟"}
        </div>
        <div style={{ color: INK, fontWeight: 700, fontSize: 30, opacity: 0.7 }}>
          {"휴대폰성지 IT 브리핑"}
        </div>
      </div>

      {/* 히어로 비주얼 */}
      <div
        style={{
          position: "absolute",
          top: 200,
          left: 64,
          right: 64,
          height: 900,
          backgroundColor: PEACH,
          borderRadius: 48,
          overflow: "hidden",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {hero ? (
          <Img src={hero} style={{ width: "100%", height: "100%", objectFit: "contain", padding: 56, boxSizing: "border-box" }} />
        ) : (
          <div style={{ fontSize: 200, fontWeight: 900, color: BRAND, opacity: 0.25 }}>{"폰스팟"}</div>
        )}
      </div>

      {/* 하단 헤드라인 블록 */}
      <div
        style={{
          position: "absolute",
          left: 64,
          right: 64,
          top: 1180,
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        <div style={{ width: 110, height: 12, backgroundColor: BRAND, borderRadius: 8, marginBottom: 18 }} />
        {l1 ? (
          <div style={{ color: INK, fontWeight: 800, fontSize: 72, lineHeight: 1.12, letterSpacing: -2 }}>{l1}</div>
        ) : null}
        {l2 ? (
          <div style={{ color: BRAND, fontWeight: 900, fontSize: 96, lineHeight: 1.1, letterSpacing: -2.5 }}>{l2}</div>
        ) : null}
        <div style={{ color: INK, fontWeight: 700, fontSize: 34, opacity: 0.55, marginTop: 22 }}>
          {"@휴대폰성지폰스팟"}
        </div>
      </div>
    </AbsoluteFill>
  );
};
