# 메타 API + GA4 + UTM 매핑 자동화 — 통합 가이드

> **새 세션 진입 시 — 이 파일부터 읽음.** 메타 광고 자동 동기화 + GA4 매칭 + UTM 매핑 시트 구조 한 번에 파악.
> 마지막 갱신: 2026-06-05

---

## 1. 한 줄 요약

**폰스팟 광고운영 관리대장 (Google Sheets) ↔ Meta Marketing API ↔ GA4 자동수집** 3자 자동화. 매일 새벽 1:30 자동 동기화 + 캠페인 단위 GA4 매칭 + UTM 표기 통일.

---

## 2. 아키텍처

```
┌─────────────────────────────────┐
│   Meta Marketing API v22.0      │
│   Ad Account: act_120320629...  │
│   System User Token (영구)       │
└───────────────┬─────────────────┘
                │ HTTPS
                ▼ 매일 01:30 자동
┌─────────────────────────────────┐
│   Google Apps Script            │
│   ├── meta-sync.gs              │
│   │   ├── syncMetaDaily         일별 합산 → 메타 시트
│   │   ├── syncMetaCreatives     광고소재 → 메타_소재 시트
│   │   ├── syncMetaCampaign★    캠페인별 → 메타_통합 시트 (신규)
│   │   ├── correctUnknownSource  GA4 출처미상 보정
│   │   ├── syncAll               위 4개 통합
│   │   └── setupUtmMapping★     UTM 매핑 시트 셋업 (신규)
│   └── Code.gs                   기존 (KPI/매트릭스/SNS)
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│  관리대장 Google Sheet           │
│  Sheet ID: 1tCGFfu2FbGo1XbigaY  │
│  PptlSbD-7Tj3PLnYH0_o9g5jI      │
├─────────────────────────────────┤
│  자동 동기화 시트:                │
│  ├── 메타 (E:G 자동)             │
│  ├── 메타_소재 (소재 라이브러리)  │
│  ├── 메타_통합 ★ (캠페인×일별)   │
│  ├── UTM_매핑 ★ (매핑 테이블)   │
│  ├── GA4_자동 (Data API)        │
│  └── 동기화_로그 (sync 이력)     │
└─────────────────────────────────┘
```

---

## 3. 시트별 역할

### 3-1. 메타 (기존)
- A~D: 종민 수기 입력 (날짜/캠페인/진행사항/비고) — 운영 메모
- **E:G 자동** (노출/클릭/지출) — syncMetaDaily가 일별 합산 입력
- H: 문의수 (수기)
- L~Q: GA4 매핑 (캠페인명 기반, 사용자 입력 캠페인 기준)
- R~Y: 월별 합계 (자동 SUMIFS)

### 3-2. 메타_소재 (자동 생성)
광고소재 라이브러리 — 메타 API의 활성/일시중지/보관 광고 전체.
- 컬럼: 광고ID/광고명/상태/헤드라인/본문/이미지URL/30일 노출/클릭/지출/CTR/CPC/평가/PS_ID/생성일/최근동기화
- 평가 = CTR 7%↑ 우수 / 4~7% 평균 / 4%↓ 저조 (지출 5,000원↑일 때만)
- PS_ID = 자동 채번 (PS-001~)
- generator.html 카피 학습용

### 3-3. 메타_통합 ★ (신규)
캠페인 × 일별 단위 통합 시트. **GA4 매칭의 정답지.**
- 컬럼: 날짜/캠페인ID/캠페인명/[utm_campaign]/노출/클릭/지출/CTR/CPC/GA4세션/카톡클릭/전화클릭/시티마켓/카톡전환률/카톡당CPC/문의수/개통수/메모
- A~H: 메타 API 자동
- D (utm_campaign): UTM_매핑 시트 VLOOKUP 자동
- I~N: GA4_자동 시트 SUMIFS (utm_campaign 기반 정확 매칭)
- O~Q: 수기

### 3-4. UTM_매핑 ★ (신규)
메타 캠페인명 (한국어) ↔ utm_campaign (영문 슬러그) 매핑 테이블.
- 컬럼: utm_campaign / utm_medium / utm_source / 메타 캠페인ID / 메타 캠페인명 / 광고세트 / 광고소재 PS_ID / 시작일 / 종료일 / 메모 / GA4 매칭상태
- A~C/G/H/I/J: 수기 (광고 등록 시 한 번)
- D~F: autoFillMetaCampaignsIntoMapping이 메타 API에서 자동 채움
- K: 자동 수식 (GA4_자동 시트에 해당 utm_campaign 있는지 검사)

### 3-5. GA4_자동 (기존)
GA4 Data API → 매일 새벽 1시 자동 수집.
- 컬럼: date / sessionSource / sessionMedium / sessionCampaignName / eventName / eventCount / sessions / totalUsers
- `sessionCampaignName` ← UTM의 `utm_campaign` 값 그대로

### 3-6. 동기화_로그 (자동 생성)
sync 함수 실행 이력 (성공/실패/메시지). 최근 500건만 유지.

---

## 4. 매일 자동 흐름 (Daily Trigger)

```
새벽 01:30 → syncAll() 자동 실행
   ├── 1. syncMetaDaily()
   │    → 메타 API "어제" 계정 단위 합산
   │    → 메타 시트 어제 날짜 행 E:G 입력
   │
   ├── 2. syncMetaCreatives()
   │    → 메타 API 활성/일시중지/보관 광고 전체
   │    → 30일 인사이트 + 평가 자동 계산
   │    → 메타_소재 시트 갱신
   │
   ├── 3. syncMetaCampaignIntegrated()  ★
   │    → 메타 API "어제" campaign 레벨
   │    → 메타_통합 시트 어제 날짜 + 캠페인 별 행 입력
   │    → D열 utm_campaign 자동 VLOOKUP
   │    → I~N (GA4 매핑) 자동 SUMIFS
   │
   └── 4. correctUnknownSource()
        → GA4_자동 (data not available) 행
        → 메모 컬럼에 [메타추정] 표시
```

---

## 5. 신규 광고 만들 때 (종민 수기)

```
1. UTM 생성기 시트에서 URL 만들기
   · utm_source = meta
   · utm_medium = display / social / video
   · utm_campaign = 영문 슬러그 (예: bom_sale_s25)
   · utm_content = image_1 (선택)

2. 광고 등록 (메타 광고관리자)
   · 캠페인명 = 한국어 OK (예: "S26 봄세일")
   · URL 매개변수에 UTM 박은 URL 사용

3. UTM_매핑 시트에 한 행 추가
   · A: utm_campaign (위에서 박은 값)
   · B: utm_medium
   · C: utm_source = meta
   · G: 광고소재 PS_ID (메타_소재 시트에서 확인)
   · H: 시작일
   · J: 메모

4. 다음날 새벽 1:30 자동 동기화 후 확인
   · 메타_통합 시트에 어제 캠페인별 데이터 자동
   · D열 utm_campaign 자동 매칭 (UTM_매핑 VLOOKUP)
   · I~N (GA4) 정확히 매핑됨
```

---

## 6. 메뉴 (시트 상단)

📡 메타 자동화:
- 🔄 지금 동기화 (테스트) — manualSyncToday
- 📥 어제 성과만 가져오기 — syncMetaDaily
- 🎨 광고소재 라이브러리 갱신 — syncMetaCreatives
- 📊 캠페인별 통합 (어제) — syncMetaCampaignIntegrated
- ⏪ 30일 백필 (1회만) — backfillMetaCampaign30Days
- 🗂 UTM_매핑 시트 셋업 — setupUtmMappingSheet
- 🔁 메타 캠페인 → 매핑 시트 자동 추가 — autoFillMetaCampaignsIntoMapping
- 🔧 메타_통합 utm_campaign 컬럼 추가 (1회) — migrateMetaIntegratedWithUtm
- 🔍 벤치마크 광고 수집 (Ad Library) — promptSyncBenchmark
- 🥊 경쟁사 광고 수집 (Ad Library) — promptSyncCompetitor
- 📤 JSON Export (generator.html용) — exportCreativesAsJSON
- 🔑 토큰 연결 테스트 — testTokenAndAccount
- ⏰ Daily Trigger 설정 — setupTriggers

---

## 7. 진행 상태 (2026-06-05)

### ✅ 완료
- Meta API 연동 (System User Token 영구)
- meta-sync.gs 기본 함수 (syncMetaDaily / syncMetaCreatives / correctUnknownSource / syncAll)
- 메타 시트 + 메타_소재 시트 자동 동기화
- generator.html v10 자동 학습 작동

### ✅ 신규 (2026-06-05)
- 캠페인 × 일별 통합 시트 (메타_통합) 함수
- 30일 백필 함수
- UTM_매핑 시트 설계 + 셋업 함수
- 메타_통합 ↔ UTM_매핑 자동 연동 (VLOOKUP)

### ⏸ 보류
- Daily Trigger 활성화 (setupTriggers 1회 실행만 하면 됨)
- Web App API 자동 갱신 (Code.gs doGet 한 줄 추가)
- 다른 채널 (구글/네이버/카카오/당근) 동일 패턴 확장

---

## 8. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| GA4 매핑 셀 모두 0 | utm_campaign ≠ GA4 sessionCampaignName | UTM_매핑 시트 A열 값 점검. GA4_자동 시트 D열과 일치하는지 |
| 메타_통합 D열 비어있음 | UTM_매핑 시트에 해당 캠페인ID 행 없음 | autoFillMetaCampaignsIntoMapping 실행 |
| `Invalid OAuth access token` | 토큰 만료 (System User Token도 60일에 한 번 갱신 권장) | 새 토큰 발급 → PropertiesService.META_TOKEN 갱신 |
| `Application request limit reached` | API rate limit | 자동 재시도 (exponential backoff). 정 안 되면 다음 동기화 사이클 대기 |
| 메뉴 안 보임 | Code.gs onOpen에 buildMetaSyncMenu_ 호출 누락 | `buildMetaSyncMenu_(SpreadsheetApp.getUi());` 추가 |
| 동기화_로그에 FAIL 누적 | 에러 알림 이메일 도착하지 않음 | ALERT_EMAIL 확인 (`phonespot86@gmail.com`) |

---

## 9. PropertiesService 키

```
META_TOKEN           = System User Token (영구. 60일에 한 번 갱신 권장)
META_AD_ACCOUNT_ID   = act_1203206295226269
```

저장: Apps Script 에디터 → 프로젝트 설정 → 스크립트 속성

---

## 10. 관련 파일

| 파일 | 위치 | 역할 |
|------|------|------|
| meta-sync.gs | `ads/code/apps_script/meta-sync.gs` | 메타 자동화 전체 코드 |
| Code.gs | `ads/code/apps_script/Code.gs` | KPI/매트릭스/SNS (기존) |
| sheet_structure.md | `ads/data/sheet_structure.md` | 시트 컬럼 구조 |
| utm_mapping_design.md | `ads/data/utm_mapping_design.md` | UTM_매핑 시트 설계 |
| MANUAL.md | `ads/MANUAL.md` | 매일/주간/월간 운영 매뉴얼 |
| README_FOR_AI.md | `ads/README_FOR_AI.md` | AI 진입점 |

---

## 11. 다음 세션 진입 시

1. **이 파일 (META_AUTOMATION.md) 먼저 읽기**
2. 종민 명령이 "메타" / "UTM" / "캠페인 매핑" / "GA4 매핑" 관련이면 → 위 흐름 따라 진행
3. 코드 변경 시 → `ads/code/apps_script/meta-sync.gs` 동기화
4. 시트 구조 변경 시 → `ads/data/sheet_structure.md` 갱신

---

작성: 2026-06-05
