import React from "react";

interface Props {
  title: string;
}

const titleSize = (title: string) => {
  const len = title.replace(/\s/g, "").length;
  if (len <= 12) return 58;
  if (len <= 18) return 52;
  return 46;
};

export const CasualTitleBar: React.FC<Props> = ({ title }) => {
  return (
    <div
      style={{
        padding: "28px 40px 24px",
        borderBottom: "5px solid #1A1A1A",
        backgroundColor: "#FFFFFF",
        fontFamily:
          "'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
      }}
    >
      <div
        style={{
          fontSize: titleSize(title),
          fontWeight: 900,
          color: "#1A1A1A",
          letterSpacing: 0,
          lineHeight: 1.18,
          wordBreak: "keep-all",
          overflowWrap: "break-word",
        }}
      >
        {title}
      </div>
    </div>
  );
};