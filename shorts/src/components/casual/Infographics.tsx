import React from "react";
import { AbsoluteFill } from "remotion";

const FONT = "'Pretendard', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif";

const SHELL: React.CSSProperties = {
  backgroundColor: "#FFF1EA",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontFamily: FONT,
  padding: "40px 56px",
  boxSizing: "border-box",
};

// ============ PriceBar ============
interface PriceBarData { label: string; before: string; after: string; }
export const PriceBar: React.FC<{ data: PriceBarData }> = ({ data }) => (
  <AbsoluteFill style={SHELL}>
    <div style={{ width: "100%", textAlign: "center" }}>
      <div style={{ fontSize: 44, fontWeight: 800, color: "#1A1A1A", marginBottom: 36 }}>{data.label}</div>
      <div style={{ display: "flex", alignItems: "center", marginBottom: 28, justifyContent: "center" }}>
        <div style={{ fontSize: 32, fontWeight: 700, color: "#999", width: 140, textAlign: "right", marginRight: 24 }}>출고가</div>
        <div style={{ width: 380, height: 64, backgroundColor: "#CCCCCC", borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: 20 }}>
          <span style={{ fontSize: 38, fontWeight: 900, color: "#1A1A1A", textDecoration: "line-through" }}>{data.before}</span>
        </div>
      </div>
      <div style={{ fontSize: 48, color: "#F74B0B", marginBottom: 16 }}>▼</div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ fontSize: 32, fontWeight: 700, color: "#F74B0B", width: 140, textAlign: "right", marginRight: 24 }}>실구매가</div>
        <div style={{ width: 260, height: 84, backgroundColor: "#F74B0B", borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 4px 0 #8a2a06" }}>
          <span style={{ fontSize: 52, fontWeight: 900, color: "#fff" }}>{data.after}</span>
        </div>
      </div>
    </div>
  </AbsoluteFill>
);

// ============ Timeline ============
interface TimelineItem { date: string; label: string; }
interface TimelineData { items: TimelineItem[]; }
export const Timeline: React.FC<{ data: TimelineData }> = ({ data }) => (
  <AbsoluteFill style={SHELL}>
    <div style={{ width: "100%", display: "flex", flexDirection: "column", alignItems: "center" }}>
      {data.items.map((item, i) => {
        const isLast = i === data.items.length - 1;
        return (
          <React.Fragment key={i}>
            <div style={{ display: "flex", alignItems: "center", gap: 36, width: "92%", justifyContent: "center" }}>
              <div style={{ width: 220, height: 140, backgroundColor: isLast ? "#F74B0B" : "#FFFFFF", border: "5px solid #F74B0B", borderRadius: 20, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 56, fontWeight: 900, color: isLast ? "#FFFFFF" : "#F74B0B", flexShrink: 0, letterSpacing: "-0.03em", boxShadow: isLast ? "0 6px 0 #8a2a06" : "none" }}>{item.date}</div>
              <div style={{ fontSize: 44, fontWeight: 800, color: isLast ? "#F74B0B" : "#1A1A1A", flex: 1, textAlign: "left" }}>{item.label}</div>
            </div>
            {!isLast && <div style={{ fontSize: 40, color: "#F74B0B", margin: "12px 0", fontWeight: 900 }}>▼</div>}
          </React.Fragment>
        );
      })}
    </div>
  </AbsoluteFill>
);

// ============ StatBig (긴 숫자 자동 폰트 축소) ============
interface StatBigData { number: string; unit?: string; label: string; }
export const StatBig: React.FC<{ data: StatBigData }> = ({ data }) => {
  const len = (data.number || "").length;
  let numFontSize = 260;
  if (len >= 8) numFontSize = 130;
  else if (len >= 7) numFontSize = 150;
  else if (len >= 6) numFontSize = 170;
  else if (len >= 5) numFontSize = 200;
  else if (len >= 4) numFontSize = 230;
  return (
    <AbsoluteFill style={SHELL}>
      <div style={{ textAlign: "center", maxWidth: "94%" }}>
        <div style={{ fontSize: 36, fontWeight: 700, color: "#666", marginBottom: 24 }}>{data.label}</div>
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "center", flexWrap: "nowrap" }}>
          <span style={{ fontSize: numFontSize, fontWeight: 900, color: "#F74B0B", lineHeight: 1, letterSpacing: "-0.05em", whiteSpace: "nowrap" }}>{data.number}</span>
          {data.unit && (
            <span style={{ fontSize: Math.min(64, Math.floor(numFontSize / 3)), fontWeight: 800, color: "#1A1A1A", marginLeft: 12, whiteSpace: "nowrap" }}>{data.unit}</span>
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ============ Compare ============
interface CompareSide { label: string; value: string; }
interface CompareData { left: CompareSide; right: CompareSide; }
export const Compare: React.FC<{ data: CompareData }> = ({ data }) => {
  const Side: React.FC<{ side: CompareSide; emphasis: boolean }> = ({ side, emphasis }) => (
    <div style={{ flex: 1, backgroundColor: emphasis ? "#F74B0B" : "#FFFFFF", border: "4px solid #F74B0B", borderRadius: 20, padding: "32px 20px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
      <div style={{ fontSize: 28, fontWeight: 700, color: emphasis ? "#FFE6D8" : "#666", marginBottom: 16, textAlign: "center" }}>{side.label}</div>
      <div style={{ fontSize: 68, fontWeight: 900, color: emphasis ? "#FFFFFF" : "#1A1A1A", textAlign: "center" }}>{side.value}</div>
    </div>
  );
  return (
    <AbsoluteFill style={SHELL}>
      <div style={{ display: "flex", width: "100%", gap: 20, alignItems: "stretch" }}>
        <Side side={data.left} emphasis={false} />
        <div style={{ display: "flex", alignItems: "center", fontSize: 56, color: "#F74B0B", fontWeight: 900 }}>→</div>
        <Side side={data.right} emphasis={true} />
      </div>
    </AbsoluteFill>
  );
};

// ============ Calendar (동적 날짜) ============
interface CalendarData { day: string; month?: string; label: string; }
export const Calendar: React.FC<{ data: CalendarData }> = ({ data }) => (
  <AbsoluteFill style={SHELL}>
    <div style={{ width: 460, backgroundColor: "#FFFFFF", border: "6px solid #1A1A1A", borderRadius: 18, overflow: "hidden", boxShadow: "0 8px 0 #8a2a06" }}>
      <div style={{ backgroundColor: "#E51010", height: 80, position: "relative" }}>
        <div style={{ position: "absolute", top: -30, left: 90, width: 18, height: 60, backgroundColor: "#1A1A1A", borderRadius: 4 }} />
        <div style={{ position: "absolute", top: -30, right: 90, width: 18, height: 60, backgroundColor: "#1A1A1A", borderRadius: 4 }} />
        {data.month && (
          <div style={{ position: "absolute", bottom: 12, left: 0, right: 0, textAlign: "center", fontSize: 26, fontWeight: 800, color: "#FFFFFF" }}>{data.month}</div>
        )}
      </div>
      <div style={{ padding: "32px 0", textAlign: "center" }}>
        <div style={{ fontSize: 200, fontWeight: 900, color: "#1A1A1A", lineHeight: 1, letterSpacing: "-0.06em" }}>{data.day}</div>
        <div style={{ marginTop: 16, fontSize: 32, fontWeight: 800, color: "#E51010" }}>{data.label}</div>
      </div>
    </div>
  </AbsoluteFill>
);

// ============ BankAccount (동적 금액) ============
interface BankAccountData { amount: string; unit?: string; account?: string; label?: string; }
export const BankAccount: React.FC<{ data: BankAccountData }> = ({ data }) => {
  const unit = data.unit ?? "원";
  const account = data.account ?? "○○○-○○-○○○○○○";
  const label = data.label ?? "잔액";
  return (
    <AbsoluteFill style={SHELL}>
      <div style={{ width: "92%", backgroundColor: "#1428A0", borderRadius: 18, border: "5px solid #0a1968", padding: 18 }}>
        <div style={{ backgroundColor: "#FFFFFF", borderRadius: 8, padding: "28px 36px" }}>
          <div style={{ fontSize: 28, fontWeight: 800, color: "#1428A0", marginBottom: 8 }}>통장</div>
          <div style={{ width: 140, height: 4, backgroundColor: "#1428A0", marginBottom: 24 }} />
          <div style={{ backgroundColor: "#F4F4F4", borderRadius: 8, padding: "16px 20px", fontSize: 32, fontWeight: 700, color: "#1A1A1A", letterSpacing: 2, marginBottom: 24 }}>{account}</div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#666" }}>{label}</div>
            <div style={{ fontSize: 56, fontWeight: 900, color: "#F74B0B" }}>
              ₩{data.amount}{unit !== "원" && <span style={{ fontSize: 32, marginLeft: 6 }}>{unit}</span>}
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
