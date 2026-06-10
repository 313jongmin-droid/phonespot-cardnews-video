# 메타 광고 자동 학습 — MD 파일 기반 (2026-06-10 신설)

> 광고 카피 작성 (generator.html) + 카드뉴스/쇼츠/뉴스 수집 시 자동 참조.
> Apps Script (meta-sync.gs) → Drive MD 파일 → Drive desktop sync → 각 task가 Read.
> 패턴: `YOUTUBE_LEARNING.md` 와 동일.

---

## 한 줄 요약

매일 새벽 메타 광고 시트 (`메타_소재` + `메타_통합`) → Gemini 분석 → **Drive `phonespot_cardnews_state/meta_insights.md`** 자동 생성. Drive desktop sync로 로컬 자동 동기화. 광고 작성 / 카드뉴스 / 쇼츠 / 뉴스 수집 task가 작업 시작 시 Read → 키워드/헤드라인 패턴/회피 패턴 자동 반영.

---

## 학습 루프

```
01:30 — syncAll (기존)
  Meta API → '메타' / '메타_소재' / '메타_통합' 시트 갱신
  · 어제 일별 성과 + 전체 광고 라이브러리 + 캠페인별 GA4 매핑

01:45 — generateMetaInsightsMarkdown ★ MD 방식 (2026-06-10)
  '메타_소재' (헤드라인/본문/30일 CTR/CPC) 분석
  '메타_통합' (캠페인별 카톡전환률/CPL) 분석
  Gemini API → Top 키워드 / 헤드라인 패턴 / 우수·회피 / 캠페인 공통점 / 다음 카피 권장
  → Drive 폴더 'phonespot_cardnews_state' / 파일 'meta_insights.md' 덮어쓰기
  → Drive desktop sync 로 사용자 PC 자동 동기화

광고 카피 작성 (generator.html):
  → meta_insights.md Read
  → 우수 헤드라인/본문 패턴 → 신규 카피 작성 시 직접 반영

카드뉴스 / 쇼츠 / 뉴스 수집:
  → INSTRUCTIONS_CARDNEWS.md / INSTRUCTIONS_SHORTS.md 의 룰
  → meta_insights.md 자동 Read
  → 후보 점수 가중치 + 스크립트 후킹 적용 (유튜브와 합산)
```

---

## Drive 저장 위치

| 항목 | 값 |
|------|-----|
| Drive 폴더 | `phonespot_cardnews_state` (유튜브와 공유) |
| 파일명 | `meta_insights.md` |
| 로컬 sync 위치 | `~/My Drive/phonespot_cardnews_state/meta_insights.md` |
| 권한 | 시트 소유자 (회사 계정) 동일 |

---

## MD 파일 구조

```markdown
# 폰스팟 메타 광고 인사이트 (자동 학습)

> 갱신: 2026-06-10 01:45 | 분석 광고 87개 | 평균 CTR 6.52% | 평균 CPC 832원

## 💡 다음 광고 카피 권장
(Gemini 직접 조언 3-5문장, 헤드라인+본문 톤)

## 📰 카드뉴스/쇼츠 후킹 적용
(메타 우수 패턴을 카드뉴스/쇼츠에 어떻게 적용할지 2-3문장)

## ★ Top 키워드 (광고 카피 우선 반영, 카드뉴스 후보 점수 +30%)
| 키워드 | 빈도 | 평균 CTR |
| 자급제 | 12 | 8.4% |
| ...

## ★ 우수 헤드라인 패턴 (적용 시 +20%)
### 숫자 포함
- "갤럭시 S26 0원 가능"
- ...
### 의문문
- "이거 진짜 0원?"
- ...

## ★ 우수 본문 패턴
...

## ★ 우수 광고 공통점
- ✓ 첫 5자에 가격/숫자
- ...

## ★ 회피 패턴 (-40% 감점)
- ✗ 추상 문구 (특별/최고 등)

## ★ 카톡전환 우수 캠페인 공통점
- 🟢 ...

## Top 10 CTR 광고
1. **[CTR 12.4% / CPC 410원]** ...

## Top 캠페인 (카톡전환 효율)
| 캠페인 | 지출 | 카톡클릭 | 카톡당CPC | 전환률 |

## 매장 정합 (휴대폰 도메인 보정)
- 모델명 + 숫자 강조
- 가격/지원금/공시지원 우선
- ...
```

---

## 적용 룰 (각 task별)

### 광고 카피 작성 (generator.html)
- 새 광고 카피 작성 전 `meta_insights.md` 자동 Read
- Top 키워드 → 헤드라인 후보 풀에 우선 포함
- 우수 헤드라인 패턴 → 신규 카피 생성 시 톤 적용
- 회피 패턴 → 명시적으로 제외

### 카드뉴스 (INSTRUCTIONS_CARDNEWS.md)
- "자체 메타 광고 학습" 섹션 (유튜브 학습 옆)
- 매 사이클 시작 시 meta_insights.md Read
- 후보 점수 가중치 (유튜브와 합산):
  - 메타 Top 키워드 매치 +30%
  - 메타 우수 헤드라인 패턴 매치 +20%
  - 메타 회피 패턴 -40%
- 후보 표에 "메타 학습" 컬럼 추가

### 쇼츠 (INSTRUCTIONS_SHORTS.md)
- Step 0 (매 영상 작업 전) meta_insights.md + youtube_insights.md 동시 Read
- shorts_script 카드 1 (후킹) TTS 멘트에 우수 패턴 적용 (둘 다 참조)

### 뉴스 수집
- 4 라인 후보 수집 시 메타 Top 키워드 가중치 자동 적용
- 후보 표 정렬에 반영

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| MD 파일 안 보임 | Drive desktop sync 안 됨 | Drive desktop 켜져있는지 / 동기화 상태 확인 |
| "유효 광고 없음" 로그 | 최소 지출 (EVAL_MIN_SPEND=5,000원) 미달 | 데이터 누적 후 자동 해결 |
| Gemini 비활성 | API key 없음 | Properties에 GEMINI_API_KEY 추가 (유튜브와 공유 가능) |
| 캠페인 통합 섹션 비어있음 | `메타_통합` 시트 비어있음 | 메뉴 → 📡 메타 자동화 → ⏪ 30일 백필 1회 실행 |
| Drive 폴더 위치 변경 원함 | 기본명 `phonespot_cardnews_state` | meta-sync.gs 의 `META_INSIGHTS_DRIVE_FOLDER` 상수 변경 |

---

## Drive desktop sync 셋업 (사용자)

유튜브와 동일 폴더 (`phonespot_cardnews_state`) 사용 → 유튜브 sync 설정 그대로면 자동 적용. 추가 작업 없음.

---

## Gemini API 설정

유튜브와 동일 키 사용. 이미 `GEMINI_API_KEY` 설정돼있으면 추가 작업 없음.

미설정 시:
1. https://aistudio.google.com/ → API Key
2. Apps Script → 프로젝트 설정 → 스크립트 속성
3. `GEMINI_API_KEY` = `<발급키>`
4. 무료 tier 일 1500 request — 유튜브(1회/일) + 메타(1회/일) 합쳐 2회/일이라 여유.

---

## 적용 순서 (사용자 측)

1. Apps Script `meta-sync.gs` 마지막에 `outputs/meta_insights_patch.js` 통째 붙여넣기 (또는 기존 setupTriggers 교체 + 신규 함수 추가)
2. `buildMetaSyncMenu_` 함수에 `.addItem('🧠 인사이트 MD 생성', 'generateMetaInsightsMarkdown')` 1줄 추가
3. (이미 있으면 skip) `GEMINI_API_KEY` 추가
4. 메뉴 → 📡 메타 자동화 → **⏰ Daily Trigger 설정** (트리거 2개 박힘: 01:30 + 01:45)
5. 메뉴 → 📡 메타 자동화 → **🧠 인사이트 MD 생성** 1회 테스트
6. Drive 가서 `phonespot_cardnews_state/meta_insights.md` 생성됐는지 확인

---

## 유튜브와의 관계

같은 폴더 `phonespot_cardnews_state` 에 두 파일 공존:

```
phonespot_cardnews_state/
├── youtube_insights.md   (03:40 갱신)
└── meta_insights.md      (01:45 갱신)
```

카드뉴스/쇼츠 task는 둘 다 Read → **두 인사이트의 가중치 합산**하여 후보 점수 산출.

---

작성: 2026-06-10 (YOUTUBE_LEARNING.md 패턴 그대로 메타 버전)
