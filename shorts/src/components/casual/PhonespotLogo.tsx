import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";

/**
 * 폰스팟 로고 화면.
 * - 종민님이 'logos/phonespot.png' (또는 .svg) 를 추가하면 그걸 사용
 * - 없으면 텍스트 기반 임시 로고 (오렌지 ●●● + 폰스팟IT 텍스트)
 *
 * 자동 fallback 위해 useState + onError 처리 — Remotion 정적 환경이라 try/catch 대신
 * 정적 텍스트 로고를 기본으로 띄움. 사용자가 PNG 추가 시 useLogoFile=true 변경.
 */

const FONT = "'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif";

interface Props {
  // 종민님 로고 파일 경로 (public/assets/logos/ 기준). 없으면 텍스트 로고.
  filename?: string;
}

export const PhonespotLogo: React.FC<Props> = ({ filename }) => {
  const useImageLogo = Boolean(filename && /\.(png|jpg|jpeg|webp|svg)$/i.test(filename));
  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#FFFFFF",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        padding: 60,
        boxSizing: "border-box",
      }}
    >
      {useImageLogo ? (
        <Img
          src={staticFile(`assets/logos/${filename}`)}
          style={{ maxWidth: "80%", maxHeight: "70%", objectFit: "contain" }}
        />
      ) : (
        <>
          {/* 임시 텍스트 로고 - 오렌지 점 3개 + 폰스팟IT */}
          <div style={{ display: "flex", gap: 14, marginBottom: 24 }}>
            <div style={{ width: 28, height: 28, borderRadius: "50%", backgroundColor: "#F74B0B" }} />
            <div style={{ width: 28, height: 28, borderRadius: "50%", backgroundColor: "#F74B0B" }} />
            <div style={{ width: 28, height: 28, borderRadius: "50%", backgroundColor: "#F74B0B" }} />
          </div>
          <div
            style={{
              fontFamily: FONT,
              fontSize: 140,
              fontWeight: 900,
              color: "#1A1A1A",
              letterSpacing: "-0.05em",
              lineHeight: 1,
            }}
          >
            폰스팟<span style={{ color: "#F74B0B" }}>IT</span>
          </div>
          <div
            style={{
              fontFamily: FONT,
              fontSize: 36,
              fontWeight: 700,
              color: "#666",
              marginTop: 20,
            }}
          >
            광교 미니 IT 브리핑
          </div>
        </>
      )}
    </AbsoluteFill>
  );
};
