# 폰스팟 홍보영상 — 타이포 & 인포그래픽 스타일 카탈로그

> 목적: 홍보영상은 "문구 확장"이 아니라 **디자인 스타일 라이브러리 확장**으로 간다.
> 아래는 타이포/인포그래픽만으로(실사 없이) 만들 수 있는 스타일을 조사·정리하고,
> 종민님 엔진(9:16, Remotion+React, Pretendard, TTS 싱크)에 매핑한 것.

## 읽는 법

- **난이도** = 우리 엔진 기준 구현 비용. ★ 순수 텍스트/CSS · ★★ 도형·바·카운터 · ★★★ 차트타이밍·가변폰트·3D
- **보유** = 이미 만든 스타일(`styles/`에 존재)
- 사운드오프 시청이 70~85%라 **모든 스타일에서 자막 가독성은 필수**(텍스트가 메시지를 운반).
- ✅ **구현 상태(2026-05-29): 비추 3종(B3·B7·B8) 제외한 14종 + 기존 3종 = 총 17종 전부 구현 완료.** `styles/<id>.tsx` + 컴포지션 `Promo-<id>`. 개념 썸네일은 `preview/promo_style_menu.png`.

---

## A. 타이포그래피 스타일 (글자가 주인공)

| # | 스타일 | 설명 | 폰스팟 활용 | 난이도 | 보유 |
|---|---|---|---|---|---|
| A1 | 비트컷 펀치 | 한 구절씩 가운데 스케일펀치, 음성 비트에 컷 | 기본 홍보 | ★ | ✅ kinetic |
| A2 | 하이라이트 박스 | 핵심 구절에 색 박스 + 슬라이드, 진행바·코너태그 | 다른 편집자 톤 | ★ | ✅ kinetic-box |
| A3 | 줄 리빌 | 구절을 stagger로 쌓아 올림(차분·또렷) | 정보 전달형 | ★ | ✅ reveal |
| A4 | 오버사이즈 훅 | 화면 꽉 채우는 초대형 단어 1개(헤비 산세리프) | 첫 3초 훅 | ★ | — |
| A5 | 카라오케 캡션 + 키워드 컬러팝 | 단어가 차례로 등장, 강조 단어만 색 박스 | 나레이션 동기화 자막(2026 표준) | ★★ | — (엔진에 chunkUtil 있음) |
| A6 | 스위스/그리드(편집형) | 좌측정렬·그리드, 큰 숫자 ↔ 작은 캡션 대비, 라인 | 신뢰·프리미엄 톤 | ★★ | — |
| A7 | 마스크 리빌 | 글자가 마스크/클립 박스 안에서 슬라이드 등장 | 고급스러운 전환 | ★★ | — |
| A8 | 가변폰트 모핑(fluid) | 한 글자가 weight/width를 바꾸며 변형 | 임팩트 한 컷 | ★★★ (Pretendard Variable 활용) | — |
| A9 | 스크롤/크롤 타이포 | 텍스트가 세로로 흐름(목록 나열) | "이런 것까지 다" 나열 | ★ | — |
| A10 | 마커/주석 레이어 | 손글씨 밑줄·동그라미·화살표로 강조 | 핵심 단어 강조 | ★★ (SVG path) | — |
| A11 | 글리치/노이즈 | 값이 깨지며 바뀌는 연출 | "막상 가면 말 바뀜" 페인 강조 | ★★ | — |

## B. 인포그래픽 / 데이터 스타일 (숫자·구조가 주인공)

| # | 스타일 | 설명 | 폰스팟 활용 | 난이도 | 보유 |
|---|---|---|---|---|---|
| B1 | 카운터(롤업 숫자) | 0→값으로 숫자 카운트업 | 절약액·건수 강조 ⚠가격숫자 규제 | ★★ | — |
| B2 | 바 비교 | 두 막대를 나란히 비교 | "정가 vs 조회가" 같은 자기 항목 비교(경쟁사 비교는 비방주의) | ★★ | — (casual엔 pricebar 존재) |
| B3 | 바차트 레이스 | 시간축 순위 경쟁 애니메이션 | 폰스팟엔 과함 → 비추 | ★★★ | — |
| B4 | 타임라인 | 시간/단계 흐름 시각화 | "예전 방식 → 폰스팟 방식" | ★★ | — (casual timeline 존재) |
| B5 | 프로세스 플로우(스텝) | 3~4단계 진행 표시 | "조회 → 확정 → 바로 개통" 3스텝 | ★★ | — |
| B6 | 체크리스트 / 대조표 | ✓/✗ 항목 비교 | "이런 거 없어요"(상담강요·말바꿈·숨은비용 ✗ / 즉시조회 ✓) | ★ | — |
| B7 | 피라미드/계층 | 중요도 순 계층 구조 | 활용도 낮음 | ★★ | — |
| B8 | 아이소메트릭 | 평면에 3D 입체 일러스트 | 실사 대체 어렵고 에셋 부담 → 비추 | ★★★ | — |
| B9 | 픽토그램/아이콘 모션 | 단순 아이콘이 등장·변형 | 개념 보조(폰·체크·자물쇠 등) | ★★ (아이콘 에셋) | — |

## C. 처리/연출 레이어 (어느 스타일에나 얹는 옵션)

비트 싱크(음성·음악) · 컬러 플래시 · 필름 그레인/노이즈 · 그라데이션 배경 이동 · 코너 브랜드 태그 · 하단 진행바 · 강제 자막(사운드오프) · 변수폰트 강조. 스타일 본체와 분리해 토글로 둘 수 있음.

---

## D. 폰스팟 추천 로드맵 (다음에 만들 순서)

근거: 휴대폰 구매 플랫폼은 "신뢰 + 명료함"이 핵심. 화려함보다 **읽히고 믿기는** 쪽.

1. **B6 체크리스트 ✓/✗** — "상담강요·말바꿈·숨은비용 없음 / 즉시조회·고정가" 한 방에. 난이도 낮고 메시지 강력. **1순위.**
2. **A5 카라오케 키워드 컬러팝** — 나레이션 동기화 자막. 2026 숏폼 표준, 체류율↑.
3. **B5 3스텝 프로세스** — "조회 → 확정 → 바로 개통" 절차의 단순함을 시각화.
4. **A4 오버사이즈 훅** — 첫 3초 전용 훅 스타일(다른 스타일과 조합).
5. **A6 스위스/그리드** — 프리미엄·신뢰 톤이 필요한 캠페인용.
6. **B2 바 비교(자기 항목)** — "정가 vs 조회가" 식. ⚠숫자·비교는 근거 있는 값만.

보류/비추: B3 바차트레이스(과함), B8 아이소메트릭(에셋·난이도), B7 피라미드(활용 낮음).

규제 메모(반복): 가격 숫자·지원금액은 실제 근거 있는 값만, 경쟁사 직접 비교/비방 금지(B2·B6은 "우리 항목" 또는 "업계 일반"으로만).

---

## E. 구현 메모

- 전부 기존 스타일 플러그인 구조에 그대로 추가됨: `styles/<id>.tsx` 1개 + `registry.ts` 한 줄 → `Promo-<id>` 컴포지션 자동 생성.
- B계열(바·카운터·타임라인)은 casual 트랙 `Infographics.tsx`에 이미 유사 로직(stat/compare/timeline/pricebar)이 있어 참고·이식 가능(복사만, casual 원본은 무수정).
- A5는 엔진의 `chunkUtil`/karaoke 개념을 promo 톤으로 재구성.

---

## 출처 (Sources)

- [Kinetic typography — Wikipedia](https://en.wikipedia.org/wiki/Kinetic_typography)
- [Kinetic Typography in 2026: Examples, Patterns & UX Risk — Digital Silk](https://www.digitalsilk.com/digital-trends/kinetic-typography/)
- [Typography Trends Shaping Short-Form AI Video Content — FontMirror](https://www.fontmirror.com/en/typography-trends-shaping-short-form-ai-video-content/)
- [Kinetic Typography for TikTok: Boost Retention — Influencers Time](https://www.influencers-time.com/kinetic-typography-boost-video-retention-on-tiktok-and-reels/)
- [Data Visualization in Motion Graphics: 5 Styles — Info-graphics](https://www.info-graphics.com/blog/data-visualization-in-motion-graphics-guide-5-styles-that-boost-product-storytelling)
- [Designing Animated Infographics for Data Visualisation — Educational Voice](https://educationalvoice.co.uk/designing-animated-infographics/)
- [Make a bar chart race — Flourish](https://flourish.studio/visualisations/bar-chart-race/)
- [Font Trends 2026 — Simplified](https://simplified.com/blog/design/creative-font-trends)
