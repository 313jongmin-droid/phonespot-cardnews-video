import React from "react";

interface Props {
  topic: string;
  channelName: string;
  opacity?: number;
}

export const TopBar: React.FC<Props> = ({ topic, channelName, opacity = 1 }) => {
  return (
    <div
      style={{
        height: 84,
        backgroundColor: "#0A0A0A",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "0 36px",
        opacity,
        fontFamily:
          "'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
      }}
    >
      <div
        style={{
          fontSize: 30,
          fontWeight: 900,
          color: "#FFFFFF",
          backgroundColor: "#F74B0B",
          padding: "6px 20px",
          borderRadius: 6,
          letterSpacing: "0.04em",
        }}
      >
        {topic}
      </div>
      <div
        style={{
          fontSize: 34,
          fontWeight: 900,
          color: "#F74B0B",
          letterSpacing: "-0.02em",
        }}
      >
        {channelName}
      </div>
    </div>
  );
};
