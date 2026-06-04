# Apps Script 함수 인덱스

> Code.gs에 들어있는 모든 함수의 역할·트리거·의존관계. 신규 작업자 인계용.

**소스 파일**: `ads/code/apps_script/Code.gs`
**마지막 sync**: 2026-05-30 (1,424줄 / 18 함수)

---

## 함수 카테고리

| 카테고리 | 설명 |
|---------|------|
| `[일상]` | 매일 자동 트리거 또는 메뉴에서 자주 실행 |
| `[수동]` | 필요할 때만 함수 셀렉터에서 직접 실행 |
| `[셋업]` | 일회성 초기 셋업 |
| `[헬퍼]` | private (_접미사). 다른 함수에서 호출 |

---

## 메뉴 구성 (onOpen 기준)

```
🛠 폰스팟 운영
├── ⚡ 전체 새로고침       → refreshAll
├── ─────────
├── 🔃 GA4 최신 데이터 가져오기 (어제)  → fetchGA4Daily
├── 📥 GA4 30일 다시 가져오기 (백필)   → fetchGA4Backfill
├── ─────────
├── 📋 SNS 월별 합계 수식 복구  → repairSNSMonthlySummaries
└── 📊 문의접수 입력률 갱신     → updateKakaoInquiryCoverage
```

---

## 함수 목록

### [일상] — 자동 실행 또는 자주 사용

| 함수 | 라인 | 역할 |
|------|------|------|
| `onOpen()` | 29 | 시트 열 때 메뉴 생성 (시간 트리거 X) |
| `refreshAll()` | 55 | GA4 수집 + KPI + 매트릭스 + SNS + 차트 + SNS합계복구 + 입력률갱신 모두 한번에 |
| `fetchGA4Daily()` | 87 | 어제 GA4 데이터 수집 (매일 새벽 1시 트리거) |
| `importGA4(start,end,clearAll)` | 111 | GA4 Data API 호출 → GA4_자동 시트 적재 |
| `updateKPISummary()` | 237 | 통합대시보드 행 9~14 (핵심 KPI 상세) 재구성 |
| `updateChannelMatrixWithGA4()` | 331 | 통합대시보드 행 17~23 (채널 매트릭스) 재구성. E16 드롭다운 기간 사용 |
| `updateSNSReport()` | 621 | 통합대시보드 행 28~33 (SNS 보고표) 재구성. E28 드롭다운 기간 사용 |
| `addTimeSeriesChart()` | 475 | 추세 시트 30일 일별 광고비/카톡클릭 차트 재생성 |
| `repairSNSMonthlySummaries(showAlert)` | 745 | SNS 시트(스레드/인스타/유튜브/틱톡)의 우측 월별 합계(K:P) 수식 복구. 시트 자동 변환 이슈로 깨질 때 |
| `updateKakaoInquiryCoverage(showAlert)` | 1203 | 문의접수 시트 우측 영역(H:Q)에 일별 카톡 입력률 대시보드 갱신 |

### [수동] — 필요시 직접 실행

| 함수 | 라인 | 역할 |
|------|------|------|
| `fetchGA4Backfill()` | 103 | 최근 30일 GA4 전체 재수집. 트리거 깨졌을 때 복구용 |
| `updateKakaoReportDashboard(showAlert)` | 1341 | 카톡 리포트 대시보드만 갱신 (입력률 제외) |

### [셋업] — 일회성

| 함수 | 라인 | 역할 |
|------|------|------|
| `setupKakaoDailyReport()` | 1017 | 문의접수 시트 H:Q 영역에 일별 카톡 리포트 헤더·구조 초기 셋업 |

### [헬퍼] — 내부 호출 전용 (_접미사)

| 함수 | 라인 | 역할 |
|------|------|------|
| `setupKakaoDailyReportHeadersOnly_(sh)` | 1185 | 카톡 리포트 헤더만 다시 박기 |
| `getInquirySheet_()` | 925 | 문의접수 시트 객체 가져오기 |
| `normalizeYmd_(value, defaultYear)` | 935 | "5월 27일" 등 다양한 형식 → YYYY-MM-DD 정규화 |
| `toNumber_(value)` | 999 | 다양한 형식 → 숫자 변환 |
| `kakaoReportCol_(offset)` | 1009 | 카톡 리포트 컬럼 위치(H열=8 기준) 계산 |

---

## 통합대시보드 셀 영역 매핑

| 영역 | 행 범위 | 관리 함수 |
|------|--------|----------|
| 기준일 (TODAY) | 1 | (수식 직접) |
| 오늘 행동 필요 알림 | 2~3 | (수식 직접) |
| KPI 카드 4개 | 4~7 | (수식 직접) |
| 핵심 KPI 상세 | 9~14 | `updateKPISummary()` |
| 채널 매트릭스 헤더 + E16 드롭다운 | 16 | `updateChannelMatrixWithGA4()` |
| 채널 매트릭스 본체 | 17~23 | `updateChannelMatrixWithGA4()` |
| 네비게이션 (상세 보기 링크) | 25~27 | (수식 직접) |
| SNS 보고표 헤더 + E28 드롭다운 | 28 | `updateSNSReport()` |
| SNS 보고표 본체 | 29~33 | `updateSNSReport()` |

### 보조 셀 (드롭다운 → 날짜 변환)

| 셀 | 의미 |
|----|------|
| `N16` / `O16` | 채널 매트릭스 시작/종료일 |
| `N28` / `O28` | SNS 보고표 시작/종료일 |

---

## 문의접수 시트 — 카톡 리포트 영역 (H:Q)

신규 추가된 카톡 일별 리포트가 문의접수 시트 **우측 H~Q 영역**에 내장됨.

```javascript
const KAKAO_REPORT_START_COL = 8;   // H열
const KAKAO_REPORT_NUM_COLS = 10;   // H~Q (10개 컬럼)
const KAKAO_REPORT_HEADER_ROW = 4;
const KAKAO_REPORT_DATA_ROW = 5;
```

→ 통합대시보드의 "📊 문의접수 입력률 갱신" 메뉴가 이 영역을 매일 갱신.

---

## 의존 관계

```
시트 「GA4_자동」 (자동수집된 GA4 원천 데이터)
  ↑ 수집: fetchGA4Daily / fetchGA4Backfill / importGA4
  ↓ 참조: updateChannelMatrixWithGA4 / updateSNSReport (간접)

시트 「메타」「구글」「네이버」「카카오」「당근」 (수동 입력)
  ↓ 참조: updateChannelMatrixWithGA4 / updateKPISummary

시트 「문의접수」 (수동 입력 + H:Q 자동 리포트)
  ↓ 참조: updateKPISummary / updateChannelMatrixWithGA4
  ↑ 갱신: updateKakaoInquiryCoverage / updateKakaoReportDashboard

시트 「스레드」「인스타」「유튜브」「틱톡」 (수동 입력)
  ↓ 참조: updateSNSReport
  ↑ 월별합계 K:P 수식 복구: repairSNSMonthlySummaries
```

---

## 위험 함수 — 절대 실행 금지 (현재 Code.gs에는 없음)

이전 버전에서 사용했던 일회성 셋업 함수들. **현재 Code.gs에서는 제거됨.** 만약 옛 백업에서 발견되면 절대 실행 X.

- `rebuildDashboard()` — 통합대시보드 전체 재구성 (옛 행 위치)
- `polishDashboardUI()` — UI 폴리시 (행 19 헤더 기준)
- `consolidateStaticSheets()` — 정적 시트 통합
- `removeBalanceTracker()` — 잔액 트래커 제거
- `masterCleanup()` — 시트 대청소 (영구 삭제 포함)
- `organizeSheets()` — 시트 색상/순서 정리
- `convertCheckboxes()` — UTM 체크리스트 → 체크박스 변환
- `updateDashboardLinks()` — 네비게이션 옛 버전
- `weeklyGA4Reminder()` — 주간 이메일 알림

---

## 외부 종속성 (Apps Script 고급 서비스)

- `AnalyticsData` (GA4 Data API) — 활성화 필수
  - 위치: Apps Script 편집기 → 서비스 → AnalyticsData 추가
  - 사용처: `importGA4()` 안에서 `AnalyticsData.Properties.runReport(...)`

---

## 상수 (Code.gs 상단)

```javascript
const GA4_PROP_ID = '534396517';
const GA4_AUTO_SHEET = 'GA4_자동';
const INQUIRY_SHEET = '문의접수';
const KAKAO_REPORT_START_COL = 8;
const KAKAO_REPORT_NUM_COLS = 10;
const KAKAO_REPORT_HEADER_ROW = 4;
const KAKAO_REPORT_DATA_ROW = 5;
```

---

작성: 2026-05-30 (Code.gs 1,424줄 / 18 함수 sync)
