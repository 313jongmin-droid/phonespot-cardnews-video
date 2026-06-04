import React from "react";

interface Props {
  channelName: string;
}

export const CasualHeader: React.FC<Props> = ({ channelName }) => {
  return (
    <div
      style={{
        height: 116,
        backgroundColor: "#F74B0B",
        display: "flex",
        alignItems: "center",
        gap: 14,
        padding: "0 40px",
        fontFamily:
          "'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
      }}
    >
      <div style={{ width: 26, height: 26, borderRadius: "50%", border: "4px solid #FFFFFF" }} />
      <div style={{ width: 26, height: 26, borderRadius: "50%", border: "4px solid #FFFFFF", opacity: 0.55 }} />
      <div
        style={{
          fontSize: 44,
          fontWeight: 900,
          color: "#FFFFFF",
          letterSpacing: 0,
          marginLeft: 6,
        }}
      >
        {channelName}
      </div>
    </div>
  );
};