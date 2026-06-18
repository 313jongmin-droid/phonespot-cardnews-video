# APIFY_INTEGRATION_GUIDE — SNS 크롤링 (경쟁사 메타 광고 벤치마크)

> **무엇:** 신원 인증 없이 Meta Ad Library(페이스북/인스타 광고 라이브러리)를 우회 수집해 경쟁사 광고를 벤치마크하는 트랙.
> **왜 Apify:** 메타 공식 Ad Library API는 신원 인증을 요구해 폐기됨(`promptSyncBenchmark`/`promptSyncCompetitor` = 인증 못 받아 사용 안 함). Apify scraper로 우회.
> **정본 코드:** `apps_script/meta-sync.js` (라인 935~ "🤖 Apify 벤치마크 수집") + `apps_script/generator.html` (🎯 벤치마크 탭).
> 이 문서는 그 코드에서 추출한 사실만 담음(2026-06-18 복원, 원본은 git 미커밋으로 이식 누락).

---

## 1. 한 줄 요약

키워드 → Apify가 Meta Ad Library를 긁어 → 시트 `벤치마크_경쟁사_광고`에 등급 매겨 저장 → 광고 카피 생성기(generator.html)가 후킹 구조 reference로 사용.

---

## 2. 구성 (실제 코드 기준)

| 항목 | 값 |
|---|---|
| Apify Actor | `curious_coder/facebook-ads-library-scraper` |
| 단가 | **$0.00075 / 광고** (예: 30건 ≈ $0.0225) |
| 토큰 | PropertiesService 스크립트 속성 **`APIFY_TOKEN`** (없으면 `getApifyToken_`가 에러) |
| API 엔드포인트 | `https://api.apify.com/v2/acts/curious_coder~facebook-ads-library-scraper/run-sync-get-dataset-items?token=…` (POST, 동기 호출) |
| 저장 시트 | **`벤치마크_경쟁사_광고`** (상수 `SHEET_BM_CP`) |
| 국가 기본값 | `KR` |
| 실행 환경 | **Web App에서만** (Apify 호출은 Apps Script가 `google.script.run`으로 수행) |

### API 입력 페이로드 (`fetchBenchmarkFromApify_`)
```js
{
  urls: [{ url: "https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=KR&q=<키워드>&search_type=keyword_unordered&media_type=all" }],
  count: <건수>,
  "scrapePageAds.activeStatus": "active",
  "scrapePageAds.countryCode": "KR"
}
```

---

## 3. 시트 구조 — `벤치마크_경쟁사_광고`

- 행 1 = 제목 / 행 2 = 컬럼 헤더(남색 배경) / 행 3~ = 데이터.
- 자동 저장 컬럼 **A~S (19열)**:

| 열 | 헤더 | 비고 |
|---|---|---|
| A | ID | `BM-NNN_<광고ID 끝 6자리>` |
| B | 구분 | `BM` |
| C | 페이지명 | snapshot.page_name |
| D | 페이지ID | |
| E | 팔로워 | page_like_count |
| F | 본문 발췌 | 본문 앞 3줄, 280자 컷 |
| G | 광고 형식 | display_format |
| H | CTA | cta_text |
| I | 게재 시작일 | start_date_formatted |
| J | 게재 위치 | publisher_platform (페북/인스타/...) |
| K | 운영 일수 | 시작일~오늘 |
| L | 위치 수 | 플랫폼 개수 |
| M | 변형 수 | collation_count |
| N | 점수 | 아래 계산식 |
| O | 등급 | ★★★/★★/★ (조건부 서식 색칠) |
| P | 썸네일 URL | 비디오 preview 또는 이미지 |
| Q | Ad Library URL | |
| R | 검색 키워드 | |
| S | 수집일 | yyyy-MM-dd |

- 생성기 매칭용 **라벨 컬럼(수기/드롭다운, `setupLabelingDropdowns`)**:
  - **T(20) 카테고리** — 9개: 휴대폰/유심만/알뜰폰/중고폰/키즈폰/효도폰/공짜폰/인터넷/인터넷+TV
  - **U(21) 후킹 구조** — 8개: 질문형/단언형/비교형/한정형/가격강조/감성·공감/위협형/FOMO형
  - **V(22) 지역** — 자유 텍스트(공백 = 전국)

### 등급 계산 (`saveBenchmarkToSheet_`)
```
운영일수: ≥90 +3 / ≥30 +2 / ≥7 +1
위치 수 : ≥4  +2 / ≥2  +1
변형 수 : ≥3  +1
→ 점수 ≥5 = ★★★ 검증됨 / ≥3 = ★★ 양호 / ≥1 = ★ 신규 / 0 = 평가 보류
```
논리: 오래·여러 채널·여러 변형으로 굴리는 광고 = 성과 검증된 것으로 간주.
중복 제거 = `ad_archive_id` 끝 8자리.

---

## 4. 사용법 (운영자)

**진입 = generator.html(Web App)의 🎯 벤치마크 탭.** (시트 메뉴 아님 — 사용자 도구는 전부 generator로 이동)

1. `🔍 Apify 검색 + 결과 미리보기` — 키워드·건수·국가 입력 → Apify 호출(약 30~60초, 비용 미리 표시 `건수×$0.00075`) → 결과 카드 + 등급 분석.
2. 좋은 광고 체크 → `💾 선택 시트 저장` (`saveBenchmarkSelectedFromGenerator` → 시트 append).
3. `📚 시트 누적분 로드` — 이미 모은 것 다시 보기. `📂 시트 직접 열기` — 시트 새 탭.
4. 시트에서 **T/U/V열 라벨링**(카테고리·후킹·지역) → 광고 카피 생성 시 `🎯 벤치마크 매칭` 박스에 자동 reference.

라벨 안 하면 생성기 벤치마크 매칭은 영구 0건(카테고리 자동 추론 X). 후킹 구조(U열)만 채워도 LLM 프롬프트 reference로 빈도 집계됨.

---

## 5. 함수 인덱스 (`apps_script/meta-sync.js`)

| 함수 | 역할 |
|---|---|
| `getApifyToken_()` | APIFY_TOKEN 로드 |
| `fetchBenchmarkFromApify_(term, count, cc)` | Apify 동기 호출 → 원시 items |
| `saveBenchmarkToSheet_(items, term)` | 등급 계산 + 중복 제거 + 시트 append |
| `applyBenchmarkGradeFormatting_(sheet)` | O열 등급 조건부 서식 |
| `searchBenchmarkViaApify(term, count, cc)` | generator.html이 `google.script.run`으로 호출 (미리보기) |
| `saveBenchmarkSelectedFromGenerator(items, term)` | 선택분만 저장 |
| `getBenchmarkForGenerator()` | 시트 → 생성기 매칭용 JSON(카테고리·후킹·지역 포함) |
| `getSemanticAdMatches(...)` | 컨셉/지역 앵글로 라이브러리·벤치마크 의미(주제) 매칭 (Gemini, GEMINI_API_KEY 필요) |
| `deleteBenchmarkFromSheet` / `deleteBenchmarksFromSheet` | 행 삭제 |
| `getBenchmarkSheetUrl()` | 시트 URL |
| `promptApifyBenchmark()` | (레거시) 시트 메뉴용 키워드 prompt |

---

## 6. 셋업 / 트러블슈팅

- **APIFY_TOKEN 등록:** Apps Script 프로젝트 → 프로젝트 설정 → 스크립트 속성 → `APIFY_TOKEN` 추가 (apify.com 콘솔에서 발급). 토큰은 Google 클라우드 저장 = `_secrets` 손실 무영향, PC 이식 무관.
- **`APIFY_TOKEN이 PropertiesService에 없음`** → 위 등록 누락.
- **`Apify 호출 실패 <code>`** → 토큰 무효 / Apify 잔액 부족 / actor 변경. 콘솔에서 잔액·actor 확인.
- **결과 0건** → 키워드가 한국 Ad Library에 광고 없음, 또는 country 코드 불일치.
- **Web App에서만** 작동 — 시트 에디터에서 generator 함수 직접 실행 시 `google.script.run` 없음.

---

## 7. 연결 관계

- **광고 생성기**(`generator.html` 🎯 벤치마크 매칭 박스) = 이 데이터의 주 소비처. 정본 = `ads/IMPLEMENTATION_GUIDE_2026-06-09.md`.
- **카드뉴스/쇼츠 후킹** = U열 후킹 구조를 reference로 차용 가능(경쟁사 가격·상품·매장 정책은 폰스팟과 다름 → 카피 복제 X, 후킹 구조만).
- SNS 자동화 전체 매트릭스 = `ads/SNS_AUTOMATION_ROADMAP.md`.

---

변경 이력
- 2026-06-18: 신설(복원). 원본 가이드가 git 미커밋이라 새 PC 이식 시 누락 → `meta-sync.js`/`generator.html` 코드에서 사실 추출해 재작성.
