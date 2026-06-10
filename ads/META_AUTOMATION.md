# 메타 API + GA4 + UTM 매핑 + 컨셉 태그 자동화 — 통합 가이드

> **새 세션 진입 시 — 이 파일부터 읽음.** 메타 광고 자동 동기화 + GA4 매칭 + UTM 매핑 (광고그룹 단위).
> 마지막 갱신: 2026-06-10 (광고그룹 단위 전환 + 1차 자동화 완성)

---

## ★ 2026-06-10 핵심 변경 (광고그룹 단위)

**기존 캠페인 단위 → 광고그룹(adset) 단위로 전환.**

### 왜?
- 사용자 운영 단위가 광고그룹 (예: BA 배너 / VA 영상)
- GA4 utm_campaign 에 박힌 값 = 광고그룹 식별자 (한글)
- 캠페인 단위로는 GA4 매칭 불가 (한 캠페인 안에 여러 광고그룹)

### 코드 변경 (`meta-sync.gs`)
1. Meta API: `level=campaign` → **`level=adset`**
2. fields: `+ adset_id, adset_name`
3. **메타_통합 시트 19컬럼** (날짜·캠페인ID·캠페인명·**광고그룹ID·광고그룹명**·노출·클릭·지출·CTR·CPC·GA4세션·카톡클릭·전화클릭·시티마켓·카톡전환률·카톡당CPC·문의수·개통수·메모)
4. `autoDiscoverCampaigns_` → **`autoDiscoverAdsets_`** (광고그룹명 기준)
5. GA4 매칭 수식: D열(캠페인명) → **E열(광고그룹명)** + `IFERROR(VLOOKUP(E${r},'UTM_매핑'!A:B,2,FALSE),E${r})` 로 한글→영문 변환
6. UTM_매핑 시트 헤더: "메타 캠페인명" → **"메타 광고그룹명(한글)"**
7. 메뉴: "📊 캠페인별 통합" → **"📊 광고그룹별 통합"** / "🔍 미매핑 캠페인 보기" → **"🔍 미매핑 광고그룹 보기"**

### 사용자 작업 (1회)
1. 메뉴 → 📡 메타 자동화 → **⏪ 30일 백필** → 운영했던 모든 광고그룹 자동 발견
2. UTM_매핑 시트 → A열 자동 추가된 광고그룹명 → **B열에 영문 슬러그 입력** (GA4_자동 D열 기준)
3. 메타_통합 시트 K~P열 (GA4 컬럼) **자동 갱신** (VLOOKUP 즉시 재계산, 별도 클릭 X)

### 주의
- 메타 insights API는 **해당 날짜 운영(노출 발생)된 광고그룹만 반환** — 6/9 활성 광고그룹 2개면 2개만 들어옴
- 모든 광고그룹 한 번에 받으려면 **30일 백필** 권고

---

## 1. 한 줄 요약

**폰스팟 광고운영 관리대장 (Google Sheets) ↔ Meta Marketing API ↔ GA4 자동수집** 3자 자동화. 매일 새벽 1:30 자동 동기화 + **광고그룹 단위 GA4 매칭** + UTM 표기 통일.

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
│   │   ├── syncMetaCampaign★    광고그룹별 → 메타_통합 시트 (level=adset)
│   │   ├── autoDiscoverAdsets_★ UTM_매핑 신규 광고그룹 자동 발견
│   │   ├── correctUnknownSource  GA4 출처미상 보정
│   │   ├── syncAll               위 4개 + fetchGA4Daily 통합
│   │   └── generateMetaInsights  Gemini 분석 → Drive MD 저장 (01:45)
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
- 컬럼: 광고ID/광고명/상태/헤드라인/본문/이미지URL/30일 노출/클릭/지출/CTR/CPC/평가/PS_ID/생성일/최근동기화/**컨셉_태그**★
- 평가 = CTR 7%↑ 우수 / 4~7% 평균 / 4%↓ 저조 (지출 5,000원↑일 때만)
- PS_ID = 자동 채번 (PS-001~)
- generator.html 카피 학습용
- **16번 컨셉_태그 컬럼 (옵션 C, 2026-06-09)**: type:value 포맷 (예: `region:광교, season:봄세일, target:전연령`). generator.html 폼이 이 컬럼 읽어 type별 박스 자동 생성. 신규 컨셉 추가 = 시트 1행 1열 입력 = 코드 변경 0. 자세한 룰: `data/seed_concept_tags.md`

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
- 🏷 **컨셉_태그 컬럼 추가 (1회)** ★ — addConceptTagColumn_ (옵션 C, 2026-06-09)
- 📊 **컨셉_태그 통계 확인** ★ — showConceptTagStats
- 🔍 벤치마크 광고 수집 (Ad Library) — promptSyncBenchmark
- 🥊 경쟁사 광고 수집 (Ad Library) — promptSyncCompetitor
- 📤 JSON Export (generator.html용) — exportCreativesAsJSON
- 📊 마지막 동기화 정보 — showLastSyncInfo
- 🔑 토큰 연결 테스트 — testTokenAndAccount
- ⏰ Daily Trigger 설정 — setupTriggers

※ UTM_매핑 관련 메뉴(setupUtmMappingSheet/autoFillMetaCampaignsIntoMapping/migrateMetaIntegratedWithUtm)는 META_AUTOMATION.md에 설계만 문서화, 실제 meta-sync.gs 함수 미작성 상태 (2026-06-09 확인). 별도 task에서 진행 예정.

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
- UTM_매핑 시트 설계 (코드 함수 미작성)
- 메타_통합 ↔ UTM_매핑 자동 연동 설계 (VLOOKUP)

### ✅ 신규 (2026-06-08)
- syncMetaAdLibrary 자동 ★등급 평가 (운영일수 + 게재위치 기반)
- evaluateAdLibraryItem_ + applyAdLibraryGradeFormatting_

### ✅ 신규 (2026-06-09) — 옵션 C 합류
- **메타_소재 시트 16번 컬럼 컨셉_태그 추가** (`addConceptTagColumn_`)
- **컨셉_태그 통계 분석** (`showConceptTagStats`)
- **Web App API: 시트→generator.html 동적 폼** (`getConceptTagsForGenerator`)
  - type별 distinct + 빈도 + 평균 CTR + 우수 등급 카운트
- **generator.html 동적 폼 섹션** 신설 ("🏷 컨셉 태그")
  - 페이지 로드시 시트에서 자동 fetch → type별 박스 자동 렌더
  - 칩 클릭 = 선택 (localStorage 자동 저장 `phonespot_selected_concept_tags`)
  - "+ 직접 입력" = 즉석 새 value 추가 (시트엔 미반영, LLM 프롬프트만 박힘)
  - **3개 LLM 프롬프트 빌더 (buildCopyPrompt / buildSloganVariationPrompt / buildImagePrompt)에 컨셉 태그 블록 자동 주입**
  - 라이브러리 통계(누적 N건/평균 CTR/우수 등급 수) LLM에 함께 전달 → 디벨롭 학습 강화
- **사람↔AI 역할분담 명문화**:
  - 컨셉 키워드 지정 = 사람(종민)
  - 카피·후킹·앵글·이미지 컨셉 다각화 = AI (초안)
  - 최종 픽 = 사람(종민)
- **신규 컨셉 추가 비용**: 시트 1행 1열 + 코드 변경 0 (O(1))
- 초기 시드 가이드: `data/seed_concept_tags.md`

### ⏸ 보류
- Daily Trigger 활성화 (setupTriggers 1회 실행만 하면 됨)
- Web App API 자동 갱신 (Code.gs doGet 한 줄 추가)
- 다른 채널 (구글/네이버/카카오/당근) 동일 패턴 확장
- UTM_매핑 함수 작성 (설계만 있음, 함수 미작성)
- Meta Ad Library API 신원 인증 (현재 400 에러, syncMetaAdLibrary 호출 시)

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
| meta-sync.gs | `ads/code/apps_script/meta-sync.gs` | 메타 자동화 전체 코드 (옵션 C 포함) |
| Code.gs | `ads/code/apps_script/Code.gs` | KPI/매트릭스/SNS (기존) |
| generator.html ★ | `ads/code/apps_script/generator.html` | Web App 호스팅 + 컨셉_태그 동적 폼 (v11+옵션C) |
| sheet_structure.md | `ads/data/sheet_structure.md` | 시트 컬럼 구조 |
| utm_mapping_design.md | `ads/data/utm_mapping_design.md` | UTM_매핑 시트 설계 |
| **seed_concept_tags.md** ★ | `ads/data/seed_concept_tags.md` | 컨셉_태그 type 화이트리스트 + 초기 시드 (2026-06-09) |
| MANUAL.md | `ads/MANUAL.md` | 매일/주간/월간 운영 매뉴얼 |
| README_FOR_AI.md | `ads/README_FOR_AI.md` | AI 진입점 |

---

## 11. 다음 세션 진입 시

1. **이 파일 (META_AUTOMATION.md) 먼저 읽기**
2. 종민 명령이 "메타" / "UTM" / "캠페인 매핑" / "GA4 매핑" 관련이면 → 위 흐름 따라 진행
3. 코드 변경 시 → `ads/code/apps_script/meta-sync.gs` 동기화
4. 시트 구조 변경 시 → `ads/data/sheet_structure.md` 갱신
5. 광고 생성/카피/슬로건 관련이면 → 옵션 C 흐름 (아래 §12) + generator.html

---

## 12. ~~컨셉_태그 동적 폼~~ (폐기, 2026-06-09)

옵션 C 컨셉_태그 시스템은 종민 결정으로 전체 제거됨. 대체: generator.html 카피 폼에 "🆕 신규 컨셉 (자유 입력)" 한 줄 input.

자세한 폐기 사유 + 시트 P열 처리: `ads/data/seed_concept_tags.md` 참조.

---

### (참조용) 폐기 전 §12 내용

### 설계 원칙
- **컨셉 지정 = 사람(종민)**: "휴대폰대란", "키즈폰", "광교 매장" 같은 키워드는 종민의 시장 감각·매장 운영 인사이트
- **카피/후킹/이미지 컨셉 다각화 = AI**: 종민이 지정한 컨셉으로 20+ 슬로건, 10+ 후킹 앵글, 5+ 이미지 컨셉 다발 생성
- **최종 픽 = 사람(종민)**: AI 초안 중 마음에 드는 것 선택 → 부사수 인계

### 데이터 흐름
```
[메타_소재 시트 16번 컬럼 컨셉_태그]
  종민이 광고 행에 "region:광교, season:봄세일, target:전연령" 박음
                ↓ (Web App API)
[google.script.run.getConceptTagsForGenerator]
  type별 distinct + 빈도 + 평균 CTR + 우수 등급 통계 반환
                ↓
[generator.html "🏷 컨셉 태그" 섹션 동적 렌더]
  type별 박스 자동 생성 (region/season/target/format/event/...)
  각 박스에 옵션 칩 + "+ 직접 입력"
                ↓ (사람 선택)
[ctx.selectedTags = ["region:광교", "season:봄세일", ...]]
                ↓
[3개 LLM 프롬프트 빌더에 자동 주입]
  - buildCopyPrompt (Claude 챗 모드)
  - buildSloganVariationPrompt (슬로건 변형 20개)
  - buildImagePrompt (이미지 프롬프트)
  → LLM은 type:value를 자연어로 해석, 라이브러리 통계까지 받아 디벨롭 정확도 ↑
                ↓
[종민 픽 → 부사수]
                ↓
[새 광고 만들면서 컨셉_태그 박음 → 라이브러리 누적 → 다음 컨셉 학습 강화]
```

### 신규 컨셉 추가 비용
- **시트 1행 1열 입력 + 코드 변경 0 (O(1))**
- 예: "휴대폰대란" 추가 → 광고 만들고 P열에 `event:휴대폰대란, urgency:긴급, format:한정수량` 박기. 끝.

### 시드 + type 화이트리스트
`ads/data/seed_concept_tags.md` 참조 (region/season/product/target/format/event/promo_type/carrier/urgency 9개 기본).

### 셋업 절차 (1회만)
1. 시트 메뉴 → 📡 메타 자동화 → **🏷 컨셉_태그 컬럼 추가 (1회)**
2. PS-001/PS-002 P열에 시드 태그 박기 (seed_concept_tags.md §3)
3. generator.html (Web App URL) 열기 → "🏷 컨셉 태그" 섹션 자동 반영 확인
4. 메뉴 → **📊 컨셉_태그 통계 확인** 으로 카탈로그 분포 점검

### 시간 단축 효과 (정량)
| 단계 | 현재 (수동) | 옵션 C |
|---|---|---|
| 컨셉 결정 | 종민 5분 | 종민 5분 (AI 불가) |
| 슬로건 발상 | 종민 30분 (3~5개) | AI 1분 (20개) |
| 후킹 앵글 | 종민 20분 | AI 1분 (10개) |
| 이미지 컨셉 | 종민 15분 | AI 1분 (5개) |
| 픽 + 인계 | 종민 5분 | 종민 5분 |
| **합계** | **75분/컨셉** | **13분/컨셉** |

→ 컨셉당 약 60분 단축. 월 5~10건이면 5~10시간 절약.

### 정직한 한계
- 신규 컨셉 첫 1~2건은 라이브러리 학습 0 → LLM 일반 마케팅 지식만 활용. 3건 이상 누적되면 통계 의미 생김.
- 태그 표기 분산 위험 ("광교"/"광교점"/"광교 매장"). 시드 가이드 §6 표기 통일 룰 준수.
- type 난립 위험. 우선 §1 화이트리스트 9개 활용. 신규 type은 운영 중 필요해질 때만.

---

작성: 2026-06-05
