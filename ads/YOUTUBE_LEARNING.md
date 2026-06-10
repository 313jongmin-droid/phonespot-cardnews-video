# 유튜브 자동 학습 — MD 파일 기반 (2026-06-05 갱신)

> 카드뉴스/쇼츠/뉴스 수집 시 자동 참조. Apps Script → Drive MD 파일 → Drive desktop sync → cardnews/shorts task가 Read.
> 작성: 2026-06-05

---

## 한 줄 요약

매일 새벽 유튜브 시트 → Gemini 분석 → **Drive `phonespot_cardnews_state/youtube_insights.md`** 자동 생성. Drive desktop sync로 로컬 자동 동기화. cardnews/shorts task가 새 작업 시작 시 Read → 키워드/후킹/회피 패턴 자동 반영.

---

## 학습 루프

```
03:30 — fetchYouTubeAnalyticsDaily
  YouTube API → '유튜브' 시트 갱신
  · A 날짜 / E 조회수 / F 좋아요 / G 구독자 / I retention

03:40 — generateYouTubeInsightsMarkdown ★ MD 방식 (2026-06-05)
  '유튜브' 시트 분석 (Gemini API)
  · Top 키워드 / 후킹 패턴 / 우수 공통점 / 회피 / 권장 룰
  → Drive 폴더 'phonespot_cardnews_state' / 파일 'youtube_insights.md' 덮어쓰기
  → Drive desktop sync 로 사용자 PC 자동 동기화

cardnews/shorts/뉴스 수집:
  → INSTRUCTIONS_CARDNEWS.md / INSTRUCTIONS_SHORTS.md 의 룰
  → youtube_insights.md 자동 Read
  → 후보 점수 가중치 + 스크립트 후킹 적용
```

---

## Drive 저장 위치

| 항목 | 값 |
|------|-----|
| Drive 폴더 | `phonespot_cardnews_state` |
| 파일명 | `youtube_insights.md` |
| Drive desktop sync 후 로컬 위치 | `~/My Drive/phonespot_cardnews_state/youtube_insights.md` (또는 사용자 sync 설정 위치) |
| 권한 | 시트 소유자 (회사 계정) 동일 |

---

## MD 파일 구조

```markdown
# 폰스팟 유튜브 인사이트 (자동 학습)

> 갱신: 2026-06-05 03:40 | 분석 영상 234개 | 평균 1,523회 | 평균 retention 42.3%

## 💡 다음 스크립트 권장
(Gemini 직접 조언 3-4문장)

## ★ Top 키워드 (스크립트 우선 반영, 후보 점수 +30%)
| 키워드 | 빈도 | 평균 조회수 |
| 갤럭시 | 18 | 3,210 |
| ...

## ★ 후킹 패턴 (제목·도입부 활용, 매치 시 +20%)
### 의문문
- "이거 진짜?"
- ...

## ★ 우수 영상 공통점 (반영)
- ✓ 첫 1초 가격 노출
- ...

## ★ 회피 패턴 (-40% 감점)
- ✗ 긴 도입

## Top 10 조회수 영상
1. **[12,400회]** ...

## Top 5 시청 지속률

## 매장 정합 우선순위 (휴대폰 도메인 보정)
- 모델명 + 숫자 강조
- 가격/지원금 우선
- ...
```

---

## cardnews/shorts/뉴스 수집 적용 룰

### 카드뉴스 (INSTRUCTIONS_CARDNEWS.md)
- "자체 유튜브 채널 학습" 섹션 (외부 트래픽 신호 다음)
- 매 사이클 시작 시 youtube_insights.md Read
- 후보 점수 가중치:
  - 우수 키워드 +30%
  - 우수 후킹 매치 +20%
  - 우수 영상 주제 유사 +50%
  - 회피 패턴 -40%
- 후보 표에 "자체 학습" 컬럼 추가

### 쇼츠 (INSTRUCTIONS_SHORTS.md)
- Step 0 (매 영상 작업 전) youtube_insights.md Read
- shorts_script 의 카드 1 (후킹) TTS 멘트에 우수 후킹 패턴 적용
- 자연스럽게 톤·구조 반영

### 뉴스 수집
- 4 라인 후보 수집 시 점수 가중치 자동 적용
- 후보 표 정렬에 반영

---

## ★ '유튜브' 시트 구조 — 절대 룰 (2026-06-08 박음)

다른 시트(메타·구글·KT 등)와 달리 **유튜브 시트만 헤더 3행 구조**. 정렬·sync 시 반드시 보존.

| 행 | 내용 | 비고 |
|---|---|---|
| 1 | `유튜브 운영 일지` (제목) + E1: 폰스팟 유튜브 계정 링크 | 절대 건드림 ❌ |
| 2 | 네비 (🏠 대시보드로) | 절대 건드림 ❌ |
| 3 | 컬럼 헤더 (날짜·포맷·주제·링크·조회수·좋아요·팔로워·운영메모·비고) | 절대 건드림 ❌ |
| 4~ | 데이터 (오름차순 정렬, 아래가 최신) | sync/정렬 영역 |

### youtube_sync.gs 룰
- `SHEET_DATA_START_ROW = 4` ★ (2 ❌, 3 ❌)
- sync `getRange(4, 1, rowCount, 9).sort(...)` — 1~3 행 절대 포함 금지
- 신규 영상 append 시작 행 = `Math.max(4, sheet.getLastRow() + 1)`

### 깨졌을 때 (헤더가 데이터 마지막으로 밀려난 경우)
1회 실행: 메뉴 → 🎬 YouTube → **🔧 시트 헤더 복구** (또는 `repairYouTubeSheetHeaders` 직접 실행)
- A열에서 "날짜" 텍스트 가진 행을 헤더로 판정 → 그 위 1행 = 네비
- 두 행을 잘라 행 2, 3 위치로 복원

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| 헤더가 행 91-92로 밀려남 | `SHEET_DATA_START_ROW`가 2/3이라 헤더까지 정렬 영역 포함 | `repairYouTubeSheetHeaders` 실행 + 상수 4로 |
| MD 파일 안 보임 | Drive desktop sync 안 됨 | Drive desktop 켜져있는지 / 동기화 상태 확인 |
| Gemini 비활성 | API key 없음 | Properties에 GEMINI_API_KEY 추가 |
| 인사이트 시트 잔재 | 이전 방식 (시트 탭) | "유튜브_인사이트" 시트 수동 삭제 |
| Drive 폴더 위치 변경 원함 | 기본명 `phonespot_cardnews_state` | youtube_sync.gs 의 INSIGHTS_DRIVE_FOLDER 상수 변경 |

---

## Drive desktop sync 셋업 (사용자)

1. Drive desktop 설치 (이미 됨)
2. Drive에서 `phonespot_cardnews_state` 폴더가 자동 생성됨 (03:40 첫 실행 시)
3. Drive desktop 설정 → 동기화 폴더 선택 → "내 드라이브" 전체 sync 또는 특정 폴더만
4. 로컬 위치 (예: `C:\Users\<user>\My Drive\phonespot_cardnews_state\`) 에서 youtube_insights.md 확인

선택: 로컬 동기화 위치를 phonespot_cardnews 폴더 안으로 심볼릭 링크 (Windows mklink)
```
mklink "C:\Users\di898\Documents\phonespot_cardnews\_state\youtube_insights.md" "C:\Users\di898\My Drive\phonespot_cardnews_state\youtube_insights.md"
```
→ cardnews/shorts task가 `_state/youtube_insights.md` 로 자연스럽게 접근

---

## Gemini API 설정 (선택)

기본 폴백 (단순 분리) 작동. 더 정확한 분석:

1. https://aistudio.google.com/ → API Key
2. Apps Script → 프로젝트 설정 → 스크립트 속성
3. `GEMINI_API_KEY` = `<발급키>`
4. 무료 tier 일 1500 request 충분

---

## 적용 순서 (사용자 측)

1. Apps Script `youtube_sync.gs` 통째 교체 (회사 계정으로)
2. (선택) `GEMINI_API_KEY` 추가
3. 메뉴 → 🎬 YouTube → **⏰ Daily Trigger 설정** (트리거 2개 박힘)
4. 메뉴 → 🎬 YouTube → **🧠 인사이트 MD 생성** 1회 테스트
5. Drive 가서 `phonespot_cardnews_state/youtube_insights.md` 생성됐는지 확인
6. Drive desktop sync 후 로컬 위치 확인
7. (선택) phonespot_cardnews/_state/ 로 심볼릭 링크

---

작성: 2026-06-05 (MD 기반 학습 루프로 갱신)
갱신: 2026-06-08 (유튜브 시트 3행 헤더 구조 + `SHEET_DATA_START_ROW = 4` 룰 박음 + `repairYouTubeSheetHeaders` 복구 함수)
