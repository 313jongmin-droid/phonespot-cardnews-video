import { PromoStyle } from "./shared";
import { kinetic } from "./kinetic";
import { kineticBox } from "./kineticBox";
import { reveal } from "./reveal";
import { oversize } from "./oversize";
import { karaoke } from "./karaoke";
import { swiss } from "./swiss";
import { mask } from "./mask";
import { fluid } from "./fluid";
import { crawl } from "./crawl";
import { marker } from "./marker";
import { glitch } from "./glitch";
import { counter } from "./counter";
import { barcompare } from "./barcompare";
import { timeline } from "./timeline";
import { steps } from "./steps";
import { checklist } from "./checklist";
import { pictogram } from "./pictogram";
// 신규 인포그래픽
import { donut } from "./donut";
import { linegraph } from "./linegraph";
import { statgrid } from "./statgrid";
import { ranking } from "./ranking";
import { gauge } from "./gauge";
import { table } from "./table";

// 새 스타일 추가 = 여기에 한 줄 추가하면 Root.tsx가 Promo-<id> 컴포지션을 자동 등록.
export const PROMO_STYLES: { id: string; label: string; cat?: string; style: PromoStyle }[] = [
  { id: "kinetic", label: "비트컷 (가운데 스케일펀치)", cat: "typo", style: kinetic },
  { id: "kinetic-box", label: "비트컷+하이라이트박스", cat: "typo", style: kineticBox },
  { id: "reveal", label: "줄 리빌 (차분)", cat: "typo", style: reveal },
  { id: "oversize", label: "오버사이즈 훅", cat: "typo", style: oversize },
  { id: "karaoke", label: "카라오케 자막 (키워드 컬러팝)", cat: "typo", style: karaoke },
  { id: "swiss", label: "스위스/그리드 (편집형)", cat: "typo", style: swiss },
  { id: "mask", label: "마스크 리빌", cat: "typo", style: mask },
  { id: "fluid", label: "가변폰트 모핑", cat: "typo", style: fluid },
  { id: "crawl", label: "스크롤/크롤 타이포", cat: "typo", style: crawl },
  { id: "marker", label: "마커/주석 강조", cat: "typo", style: marker },
  { id: "glitch", label: "글리치/노이즈", cat: "typo", style: glitch },
  { id: "counter", label: "카운터 (롤업 숫자)", cat: "info", style: counter },
  { id: "barcompare", label: "바 비교", cat: "info", style: barcompare },
  { id: "timeline", label: "타임라인", cat: "info", style: timeline },
  { id: "steps", label: "3스텝 프로세스", cat: "info", style: steps },
  { id: "checklist", label: "체크리스트 ✓/X", cat: "info", style: checklist },
  { id: "pictogram", label: "픽토그램/아이콘", cat: "info", style: pictogram },
  { id: "donut", label: "도넛/퍼센트 링", cat: "info", style: donut },
  { id: "linegraph", label: "라인 그래프 (추세)", cat: "info", style: linegraph },
  { id: "statgrid", label: "KPI 카드 그리드", cat: "info", style: statgrid },
  { id: "ranking", label: "랭킹 Top-N", cat: "info", style: ranking },
  { id: "gauge", label: "게이지/미터", cat: "info", style: gauge },
  { id: "table", label: "대조표 (2열 비교)", cat: "info", style: table },
];

export const getStyle = (id: string): PromoStyle =>
  (PROMO_STYLES.find((s) => s.id === id) ?? PROMO_STYLES[0]).style;

// 효과음을 '섹션 역할'이 아니라 '스타일(=화면 모션)'에 맞춰 선택.
// 음원 6종: punch(임팩트)·pop(짧은 팝)·tick(똑딱)·whoosh(스윕)·ding(확정 차임)·glitch(디지털 노이즈)
export const SFX_BY_STYLE: Record<string, string> = {
  // 스케일펀치/대형 = 묵직한 임팩트
  kinetic: "punch", "kinetic-box": "punch", oversize: "punch",
  // 차분한 리빌/모핑/선 = 부드러운 스윕
  reveal: "whoosh", mask: "whoosh", fluid: "whoosh", crawl: "whoosh", linegraph: "whoosh",
  // 키워드 팝/슬램/등장 = 짧은 팝
  karaoke: "pop", marker: "pop", barcompare: "pop", steps: "pop", pictogram: "pop", statgrid: "pop", ranking: "pop",
  // 그리드 스냅/카운트/게이지/표 = 똑딱
  swiss: "tick", counter: "tick", timeline: "tick", donut: "tick", gauge: "tick", table: "tick",
  // 글리치 전용
  glitch: "glitch",
  // 체크 확정 = 차임
  checklist: "ding",
};

// 우선순위: (호출부) data.sfx > 스타일 기본 > 역할 fallback
export const sfxForStyle = (styleId: string, isCta: boolean): string =>
  SFX_BY_STYLE[styleId] || (isCta ? "ding" : "whoosh");

// 디렉터 컷(쇼케이스): 비트마다 최적 스타일 배치 — 광고 의뢰용 베스트 컷
export const PROMO_SHOWCASE: Record<string, string> = {
  open: "oversize",       // 초대형 훅
  hook: "kinetic",        // 빠른 비트컷
  fact_1: "glitch",       // 문제(말이 바뀐다) = 글리치 텐션
  fact_2: "kinetic-box",  // 해결(그대로 개통) = 하이라이트 박스 페이오프
  fact_3: "checklist",    // 신뢰(비교) = 체크리스트 proof
  cta: "kinetic-box",     // CTA 드라이브
  out: "kinetic",
};

// styleMap 프리셋 — 선택만 하면 되는 디렉터 컷 모음
export const PROMO_PRESETS: Record<string, Record<string, string>> = {
  showcase: PROMO_SHOWCASE,
  punchy: { open: "oversize", hook: "kinetic", fact_1: "glitch", fact_2: "kinetic", fact_3: "kinetic-box", cta: "kinetic", out: "kinetic" },
  calm: { open: "reveal", hook: "reveal", fact_1: "swiss", fact_2: "mask", fact_3: "swiss", cta: "reveal", out: "reveal" },
  data: { open: "oversize", hook: "kinetic", fact_1: "table", fact_2: "barcompare", fact_3: "checklist", cta: "kinetic-box", out: "kinetic" },
};
