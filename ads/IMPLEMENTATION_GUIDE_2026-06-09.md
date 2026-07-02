# 폰스팟 광고 자동화 — 2026-06-09 통합 적용 가이드

> **★ 이 문서는 다음 클로드 세션용 참조 문서입니다.** 종민이 읽는 운영 매뉴얼이 아니라, 다른 클로드 세션이 이 폴더에 진입했을 때 즉시 컨텍스트 파악 + 종민 짧은 명령에 즉시 작동하기 위한 가이드.
> 종민 액션(Apify 토큰 발급, Code.gs 박기, 새 버전 배포 등)은 이번 세션에서 종민이 이미 안내받음. 다음 세션의 종민은 그걸 다시 안내받을 필요 X.
>
> 마지막 갱신: 2026-06-12 (이번 세션 34 task 완료)
>
> **첫 진입 시 클로드 행동**:
> 1. 이 파일의 §10 변경 이력 + §13 결산으로 **현재 시스템 상태** 파악
> 2. §6 함수 인덱스로 **코드 위치** 파악
> 3. §12 디자인 토큰 + `styles.html`로 **디자인 시스템** 파악
> 4. 종민 명령 받음 → §14 작업 후보와 매칭 → 진행

---

## 0. 한 줄 요약

**시트 = 데이터 저장소 + 자동화 백엔드 / generator.html(Web App) = 사용자 도구 통합.**
- 시트 메뉴(📡 메타 자동화) = 매일 자동 동기화 + 트리거 + 토큰 테스트만 (운영자가 시트에서 다루는 자동화)
- generator.html = 카피 생성 + 슬로건 변형 + 이미지 프롬프트 + **🎯 Apify 벤치마크 수집/관리** + 라이브러리

---

## 0-1. ⚠️ 최신 아키텍처 (2026-06-12 세션 2) — 여기부터 읽어라. 아래 §2~6은 일부 구버전

생성기 핵심이 이 세션에서 크게 바뀜. 현재 상태:

- **결과 구조**: 🎲 **8행 랜덤 변주(1순위)** → ✨ 라이브러리 추천 → 🎯 벤치마크 추천. (시드카드 폐기)
  - 변주 1행 = **후킹 1 × 톤 1 단일 조합** + 예상스타일 + 거친 로컬샘플(`fillSlots`) + 행별 🖋️슬로건/🎨이미지 복사. **🎲 다시뽑기**로 재추출.
  - 축 고정/랜덤: 폼에서 **체크한 축은 고정, 비운 축은 랜덤**. 톤 9 × 후킹 8 = 72방향. 톤≡후킹 의미중복(공감×공감 등) 차단(`TONE_HOOK_EQUIV`).
- **폼 축**: 카테고리·타겟·시즌·제품·USP·길이 + **톤(정서, 9개)** + **후킹 구조(문장 골격, 8개 `c-hooks`: 질문형/단언형/비교형/한정형/가격강조/감성·공감/위협형/FOMO형)** + 지역 + 신규컨셉. (입력 가이드 섹션은 삭제됨)
- **`buildCopyPrompt` = 목적 / 지정값 / 규칙 / 출력 4단** (브랜드본질벽·패턴풀 60개·자가검증 제거). 단일조합이면 "N개 전부 이 후킹×톤 한 방향, 섞지 말 것" 강제 + 행별 **12개**.
- **1:1 매핑** (슬로건·이미지 공통): 변주 = 참고 없음 / 라이브러리 = 라이브러리만 / 벤치마크 = 벤치마크만. `buildCopyPrompt` base에서 라이브러리·벤치마크 블록 제거 → `buildLibraryEnrichedPrompt`/`buildBenchmarkEnrichedPrompt`가 `# 출력 양식` 앞에 자기 참고만 주입. `buildImagePrompt(ctx, tone, layout, refMode)` — refMode='none'/'library'/'benchmark'/'both'.
- **이미지 = 완성 배너**: "빈 공간 남겨/텍스트 그리지마" 제거 → 헤드라인+서브카피+CTA버튼+스티커 박힌 **바로 쓰는 배너**(한글 in-image, gibberish·빈칸 금지). **아트 디렉션 매 생성 랜덤**(`AD_STYLE_POOL` 12종: 만화팝/플랫볼드/네온/카와이/3D/레트로/Y2K/페스티벌/콜라주/볼드미니멀/그라데이션/타블로이드) = 포맷 고정 / 디자인은 매번 다른 디자이너.
- **지역·신규컨셉 = 모든 카피 무조건 반영**: `regionEmphasis`/`conceptEmphasis` — 키워드 단순 삽입 ❌, **앵글을 후킹의 중심**으로, 빠진 카피는 폐기, 단 표현·각도는 다양하게(단어반복 룰 충돌 회피).
- **Gemini 의미 매칭**(`getSemanticAdMatches` @ meta-sync.gs): 컨셉/지역 앵글로 라이브러리·벤치마크 광고를 **주제 유사도**로 평가 → 카테고리 달라도 추천("액정 깨진" ↔ "중고폰 보상"). `searchLibraryMatching`/`searchBenchmarkMatching`가 `currentGuide.semanticScores` 병합(임계 55). google.script.run 호출, **GEMINI_API_KEY + 배포 웹앱 필요**, 외부 URL 모드면 스킵.
- **신규 상수**: ALL_TONES_V / ALL_HOOKS_V / TONE_STYLE_V / HOOK_STYLE_V / HOOK_PATTERN_HINT / TONE_HOOK_EQUIV / AD_STYLE_POOL.
- **신규/변경 함수**: drawVariationCombos, roughSampleForCombo_, renderVariations, redrawVariations, variationCtx_, copyVariationSlogan, copyVariationImage, copyBoxImagePrompt_, copyLibraryImagePrompt, copyBenchmarkImagePrompt, requestSemanticMatch, setSemanticLoading + buildCopyPrompt·buildImagePrompt·searchLibraryMatching·searchBenchmarkMatching 재작성.
- **1·2 정리**: USP = 고정 팩트 슬롯 / 신규컨셉 = 발전하는 앵글(트렌드·페인포인트). **보류**: 컨셉 시트 저장(컨셉_뱅크), 코어 완전 hard-lock.
- **슬로건→이미지 연결** (`copyImageWithHeadline`): 변주 박스에 `#img-headline` 입력칸 → LLM에서 고른 실제 헤드라인 붙여넣고 🎨 누르면 그 문구 그대로 박힌 완성 배너 프롬프트(폼 ctx + 랜덤 아트). 변주 🎨(자동 작문)와 별개.
- **길이/타겟 실반영** (buildCopyPrompt): `lengthRule` — 짧게/중간/길게 선택 시 **전부 그 길이 통일**, "자유"일 때만 분포(20/28/32/20). `targetRule` — 특정 세대·성별 선택 시 "어휘·고민·말투가 그 대상에 밀착" 강제(값만 나열 ❌), 전연령·전체면 미적용.
- **dead code 제거**: buildCopyPrompt에서 옛 미사용 변수(conceptBlock/regionBlock/examplesBlock/bmBlock/patternSample/directionBlock 등) 삭제 → 함수가 dist부터 바로 시작.
- **변경 상세 + 알려진 함정** = `CLAUDE.md` STEP 8 "2026-06-12 (세션 2)".

**★ 2026-06-24 추가 (브랜드 프로필 범용화 + 캐러셀 4컷) — 이 블록이 최신:**
- **목적**: 생성기 폰스팟 전용 하드코딩 → **⚙설정 폼 기반 도메인 범용화**. 화장품/KT 등 코드 수정·재배포 없이 폼만으로 전환.
- **브랜드 프로필 (generator.html ~3282~3428)**: ⚙설정 탭 "🏷️ 브랜드 프로필" 폼. 활성 프로필 = 전역 `BP`(빌더가 `${BP.x}` 직접 참조), `applyBP()`가 폼/localStorage에서 갱신 + 카테고리 옵션·타이틀·패턴풀(`CATALOG.copyPatterns`) 재구성. 필드 = brandName/brandUrl/categories/copyEssence(카피 #목적)/sloganDiff(슬로건 차별점)/imageDomain/imageProductDefault/imageHeadlineFlavor/imageCallout/benchKeywords/patternPool. 기본 프로필 `폰스팟` = `DEFAULT_BP` 상속(빈 객체, 삭제 불가) → **출력 바이트 동일 = 회귀 안전(node 실행 검증함)**.
- **파라미터화 빌더**: `buildCopyPrompt`(목적=brandName/brandUrl/copyEssence), `buildSloganVariationPrompt`(brandName/brandUrl/sloganDiff), `buildImagePrompt`(imageDomain/imageHeadlineFlavor/imageCallout), `mapProductToEnglish`(기본값 폴백=BP.imageProductDefault).
- **신규 함수**: DEFAULT_BP, DEFAULT_PATTERNS(원본 풀 스냅샷), defaultPatternPoolText, parsePatternPool, loadBrandProfiles, persistBrandProfiles, getBP, applyBP, bpVal/bpSet, renderBpSelect, bpFillForm, bpFieldsFromForm, onBpSelect, bpNew, bpSave, bpDelete, bpPushSheet, bpPullSheet.
- **영속화**: localStorage `phonespot_brand_profiles`(이름→프로필 map) + `phonespot_active_profile`. ☁시트 백업/⬇불러오기 = Code.js `pushBrandProfilesToSheet`/`getBrandProfilesFromSheet` (시트 `브랜드_설정` A1=JSON·B1=시각, 자동 생성. Code.js ~1461).
- **캐러셀 4컷 (generator.html ~3431~3520)**: 📝카피 탭 "🎠 캐러셀 4컷 프롬프트 생성" 버튼 + `#carousel-section`. `CAROUSEL_BEATS`(후킹→오퍼/큰숫자→차별·조건제거→클로징+CTA) + `buildCarouselSlidePrompt_` + `generateCarousel`(톤·`AD_STYLE_POOL` 1종·제품을 **1회 고정** → 4컷 색·아트디렉션·타이포 통일) + copyCarouselSlide/copyCarouselAll. **1:1(1080²) 고정**, CTA 버튼은 4컷째만, 인디케이터 N/4. 브랜드 프로필(BP) 자동 반영.
- **실사/인스타 감성 모드 (generator.html)**: 📝카피 탭 씬 셀렉트(`#realistic-scene`: product/human/mascot) + 텍스트 셀렉트(`#realistic-text`: none/minimal) + "🎞 실사/인스타 감성 프롬프트" 버튼 + `#realistic-section`. `REALISTIC_SCENES`(3) + `REALISTIC_TEXT`(2) + `buildRealisticPrompt(ctx,textMode,sceneMode)`(디자인 배너 규칙 대신 **포토리얼 UGC**: 아마추어 폰카·자연광·생활감 실내·얕은 심도 + "광고처럼 안 보이게" 강제, 헤드라인/CTA/스티커 금지, 제품=씬 안 실물) + generateRealistic/copyRealistic. 1:1, BP 반영. `buildImagePrompt`(디자인 배너)와 **별개 트랙**.
- **★ 함정**: ① 백업 `.v_*.js/.html`을 `apps_script/` 안에 두면 **배포 깨짐** — `.clasp.json rootDir=""` → 전체 .js/.html clasp push → 함수 중복. 백업은 `apps_script_backups/`(clasp 미푸시). GitHub Actions 게이트는 `apps_script/*.js`만 검사. ② `BP`는 applyBP() 시점 갱신 전역 → 프로필 전환 후 applyBP 미호출 시 옛 값. ③ patternPool 빈값=기본 풀(DEFAULT_PATTERNS), 폼 텍스트가 기본과 동일하면 저장 안 함. ④ 캐러셀=프롬프트 생성일 뿐 이미지 아님, 모델 컷별 독립 생성이라 제품샷 드리프트(완전 동일=레퍼런스 고정 필요).
- **보류(이어할)**: 100% 자율(URL/한줄 → 프로필 AI 자동생성 또는 프로필 제거) + "판매까지"(전환소재 / 풀퍼널 콘텐츠 / 실제 판매 플랫폼 연동) = 범위 미정, 별도 진행. 기존 보류(컨셉_뱅크·코어 hard-lock) 유지.

---

## 1. 셋업 상태 (이미 완료, 참고만)

종민이 2026-06-12 세션에서 셋업 완료. 현재 상태:
- ✅ Apify 토큰 → Apps Script Properties `APIFY_TOKEN`에 저장 (보안: Regenerate 필요)
- ✅ `meta-sync.gs` 1,116줄 — Apify 함수 11개 + 메타 동기화 포함
- ✅ `generator.html` 2,863줄 — 카피·이미지·벤치마크·비율 변환 통합
- ✅ `Code.gs` doGet + include 함수 (createTemplateFromFile + evaluate)
- ✅ `styles.html` 377줄 — 디자인 시스템 분리
- ✅ 새 버전 Web App 배포 완료
- ✅ 시트 메뉴 `📡 메타 자동화` (사용자 도구 제거, 자동화만)
- ✅ Daily Trigger 매일 01:30 syncAll 작동

→ 클로드는 셋업 상태 가정하고 작업. 깨졌으면 종민이 알려줌.

---

## 2. 새 UI 가이드 (generator.html)

### 2-1. 탭 4개
```
📝 카피 생성  |  📚 라이브러리  |  🎯 벤치마크  |  ⚙ 설정
```

### 2-2. 📝 카피 생성 탭

**카피 입력 폼 변경**:
- 🆕 **신규 컨셉 입력바** (자유 입력 한 줄, 노란색 박스) — 폼 슬롯에 없는 새 컨셉 ("휴대폰대란", "키즈폰", "광교매장 픽업" 등) 자유 입력
- 카테고리·연령·성별·시즌·제품·USP·감정·키워드·톤 (기존)

**생성 모드 버튼 2개**:
- **📚 라이브러리 + 벤치마크 기반 생성** — 사전 정의 60+ 패턴 + 메타 검증 카피 + 벤치마크 후킹 3개 = 20개 즉시 출력
- **🤖 LLM 프롬프트 생성** — Claude/GPT 챗에 붙여넣을 강화 프롬프트 복사
  - 신규 컨셉은 LLM 모드에서만 반영 (라이브러리 모드는 정적 패턴이라 자유 텍스트 안 박힘)

**보조 버튼**:
- 🎲 랜덤 채우기 — 모든 슬롯 랜덤 픽
- 🧹 전체 초기화 — 폼 + 카피 결과 다 비움

**카피 카드 배지 (4종)**:
- ✨ 검증 (녹색 보더, 좌측) — 폰스팟 자체 메타 CTR 7%+ 카피
- 🎯 **벤치마크** (보라색 보더, 좌측) — 경쟁사 90일+ 운영 광고 본문 첫 줄 (`isBenchmark` 플래그)
  - 페이지명·운영일수·등급·원문 링크 메타 표시
- 🔄 운영중 (주황) — 이미 라이브러리에 있는 헤드라인
- 🆕 신규 (회색) — 새 템플릿 카피

**카드 액션**:
- 📋 슬로건 — 선택 카피 변형 20개 LLM 프롬프트 복사
- 🎨 이미지 — 영문 이미지 프롬프트 복사 (라이브러리 디자인 코드 + 벤치마크 코드 자동 박힘)

### 2-3. 🎯 벤치마크 탭 ★ 신설

**검색바**:
- 키워드 (예: "휴대폰성지")
- 국가 (KR)
- 광고 수 (1~200, 기본 20)

**버튼 3개**:
- 🔍 **Apify 검색 + 결과 미리보기** — Apify 새 호출 (모드: 검색)
- 📚 **시트 누적분 로드** — 시트에 저장된 BM 광고 표시 (모드: 시트)
- 📂 **시트 직접 열기** — Google Sheets 새 탭

**모드 배지** (결과 영역 좌상단):
- 🔍 Apify 새 검색 (파란색)
- 📚 시트 누적분 (보라색)

**결과 카드**:
- 썸네일 + 페이지명 + ★등급 배지
- 운영일수 / 노출 채널 / 변형 수 / 팔로워 / 광고 형식 / CTA
- 본문 발췌 (첫 300자)
- 모드별 액션:
  - 검색 모드 → 우측 [✓ 선택]
  - 시트 모드 → 우측 [✓ 선택] + 🗑 삭제 + BM-XXX ID 배지 + 검색키워드·수집일 메타

**일괄 액션**:
- 검색 모드: 💾 선택 시트 저장
- 시트 모드: 🗑 선택 삭제 (시트에서 영구 삭제)

**📊 디자인 패턴 자동 분석**:
- 광고 형식 분포 / CTA 분포 / 노출 채널 / 페이지별 분포
- 평균 운영일수 / 평균 변형 수 / ★★★ 검증 수
- 후킹 키워드 빈도 (본문 첫 줄)

### 2-4. 자동 import (페이지 로드 1.2초 후)
Web App 열면 자동으로 `getBenchmarkForGenerator` → 시트의 BM 광고 전체를 `library` 배열에 합류 + 우하단 토스트.

---

## 3. 데이터 흐름

```
[Apify Meta Ad Library Scraper]
    ↓ (UrlFetchApp, run-sync-get-dataset-items)
[Apps Script: fetchBenchmarkFromApify_]
    ↓ (자동 ★등급 부여 — 운영일수+채널수+변형수)
[시트: 벤치마크_경쟁사_광고 (SHEET_BM_CP)]
    ↓ (getBenchmarkForGenerator API)
[generator.html: library 배열 (isBenchmark: true)]
    ↓ (generateCopiesTemplate)
[카피 결과 카드: 🎯 벤치마크 배지]
    ↓ (buildCopyPrompt / buildImagePrompt)
[LLM 프롬프트 reference 블록 자동 박힘]
    ↓
[종민 픽 → 부사수]
```

---

## 4. 시트 메뉴 (📡 메타 자동화) — 자동화·백엔드만

남기는 항목 (운영자 자동화 도구):
- 🔄 지금 동기화 (테스트)
- 📥 어제 성과만 가져오기
- 🎨 광고소재 라이브러리 갱신
- 📊 캠페인별 통합 (어제)
- ⏪ 30일 백필 (1회만)
- 📊 마지막 동기화 정보
- 🔑 토큰 연결 테스트 (메타)
- ⏰ Daily Trigger 설정

폐기된 항목 (generator.html로 이동):
- ~~🤖 Apify 벤치마크 수집~~ → 벤치마크 탭 🔍 검색
- ~~🔍 벤치마크 / 🥊 경쟁사 (Meta Ad Library 인증 필요)~~ → 신원인증 불가, 폐기
- ~~📤 JSON Export~~ → generator가 직접 호출
- ~~🏷 컨셉_태그 컬럼 추가 / 📊 컨셉_태그 통계~~ → 옵션 C 폐기

폐기된 함수들은 코드에 남아있음 (호환·복구용, 메뉴에서만 제거).

---

## 5. 신규 함수 인덱스

### Apps Script (meta-sync.gs, 2026-06-09 추가)
| 함수 | 용도 |
|---|---|
| `getApifyToken_()` | PropertiesService에서 APIFY_TOKEN 안전 로드 |
| `fetchBenchmarkFromApify_(term, count, country)` | Apify scraper 동기 호출 |
| `saveBenchmarkToSheet_(items, term)` | 시트 저장 + 자동 ★등급 |
| `applyBenchmarkGradeFormatting_(sheet)` | 등급 색상 자동 |
| `promptApifyBenchmark()` | (메뉴 폐기) 시트 메뉴 단발 |
| `searchBenchmarkViaApify(term, count, country)` | generator.html 호출용 API |
| `saveBenchmarkSelectedFromGenerator(items, term)` | 사용자 픽 광고 저장 |
| `getBenchmarkForGenerator()` | 시트 누적분 → generator 로드 |
| `deleteBenchmarkFromSheet(idOrAdId)` | BM ID 1건 시트 삭제 |
| `deleteBenchmarksFromSheet(ids[])` | BM 다중 삭제 |
| `getBenchmarkSheetUrl()` | 시트 직접 링크 (gid) |

### generator.html (2026-06-09 추가)
| 함수 | 용도 |
|---|---|
| `searchBenchmark()` | Apify 검색 호출 |
| `loadBenchmarkFromSheet()` | 시트 누적분 로드 |
| `renderBenchmarkResults()` | 카드 그리드 렌더 (모드별) |
| `renderBenchmarkAnalysis()` | 디자인 패턴 자동 분석 |
| `toggleBenchmark(i)` / `bmSelectAll(on)` | 선택 토글 |
| `saveBenchmarkSelected()` | 검색 결과 → 시트 저장 |
| `deleteBenchmarkOne(sheetId, idx)` | 단건 삭제 |
| `deleteBenchmarkSelected()` | 다중 삭제 |
| `openBenchmarkSheet()` | 시트 새 탭 |
| `fetchBenchmarkFromSheetIntoLibrary()` | 페이지 로드 시 자동 import |
| `buildBenchmarkDesignBlock_()` | 이미지 프롬프트 벤치마크 디자인 코드 |
| `analyzeWinningDesigns_()` / `buildLibraryDesignBlock_()` | 라이브러리 디자인 분석 |
| `generateCopiesFromLibrary()` / `generateCopiesViaLLM()` | 카피 생성 분리 |
| `resetAllForm()` | 폼 + 카피 결과 전체 초기화 |

---

## 6. LLM 프롬프트 강화 내역

### buildCopyPrompt (25개 카피 생성)
1. 🆕 신규 컨셉 → 절반(13개)에만 자연스럽게 반영 강제
2. **브랜드 본질 5가지** (호기심 갭, 즉시 가격 확인, 옛 방식↔폰스팟 대조 등)
3. **자체 라이브러리 우수 사례** 최대 5개 (CTR 7%+)
4. **🎯 벤치마크 우수 사례** 최대 5개 (90일+) + 빈출 후킹 단어 통계
5. **엄격 규칙 7개**:
   - 단어 반복 ≤ 3회 (예시: 종민이 본 "재고확인 13/24" 위반 명시)
   - 길이 분포 강제: 8자(5) + 9-14자(7) + 15-20자(8) + 21+(5) = 25
   - 단순 단어 조합 ❌
   - 가격 명시 ❌
   - 인물 묘사 ❌
   - 반복 패턴 ❌
6. 패턴 풀 60+ → 무작위 8개만 발췌
7. 출력 형식: **마크다운 표** (JSON 폐기) + 자가검증 라인 강제

### buildSloganVariationPrompt (20개 변형)
- 동일 brand voice + 단어 반복 제한 + 길이 분포 (참고 슬로건 ±5자)
- 출력: 표 (번호/슬로건/글자수/변형 포인트)

### buildImagePrompt (영문 이미지 프롬프트)
- 🆕 신규 컨셉 → primary axis로 박힘
- 라이브러리 우수 광고 디자인 코드 자동 분석 (색상·스타일 키워드 추출)
- 🎯 벤치마크 디자인 코드 자동 분석 (광고 형식·CTA 분포)
- 폰스팟 visual DNA 유지 (경쟁사 video-heavy 톤 학습은 X, 폰스팟 static image 톤 유지)

---

## 7. 비용 추정

| 항목 | 비용 |
|---|---|
| Apify 광고 1건 | $0.00075 (≈ 1원) |
| 검색 1회 30개 | $0.0225 (≈ 30원) |
| 월 10키워드 × 30개 | $0.225 (≈ 300원) |
| 월 20키워드 × 100개 | $1.5 (≈ 2,000원) |
| Apps Script / Web App | 무료 |
| Meta Marketing API | 무료 (자체 광고 API) |

폰스팟 운영 규모 = **월 1,000~5,000원**. 무료 플랜 $5/월 크레딧 안에서 충분.

---

## 8. 정직한 한계 (재확인)

1. **Apify 결제 카드 등록 필요** — Pay-as-you-go. 무료 크레딧 $5/월 있지만 카드는 입력해야.
2. **간접 성과만**: Meta Ad Library는 CTR/지출 비공개. 대신 운영일수 + 채널수 + 변형수로 ★등급.
3. **벤치마크 카피는 reference 용도**: 동탄 도매폰센타 같은 경쟁사는 본문 1,500자 SNS 스타일. 폰스팟 광고로 직접 복제 X. 후킹 영감만 가져오기.
4. **첫 Apify 호출 30~60초**: Actor 부팅 시간. 카드 렌더 전 로딩 인내.
5. **삭제는 영구**: 시트 행 삭제 후 복구 X. 다시 Apify 호출해야.
6. **파일 손상 이력 (이번 세션 4회)**: 큰 Edit 누적 시 generator.html 끝부분 잘림 → outputs/phonespot/ads/generator.html 백업본으로 매번 복구. **백업본 보존 중요**. 다음에 큰 변경 시 통째 Write 권장.
7. **Apify 토큰 채팅 노출**: 셋업 끝나면 즉시 Regenerate 권장.

---

## 9. 다음 세션 진입 시 (다른 Claude/종민)

1. 이 파일 (IMPLEMENTATION_GUIDE_2026-06-09.md) + `META_AUTOMATION.md` 먼저 읽기
2. generator.html 위치: `ads/code/apps_script/generator.html`
3. 사용자 도구는 전부 Web App URL에서 (시트 메뉴 X)
4. 새 기능 추가 시 작은 Edit으로 쪼개기 (파일 손상 방지)
5. 변경 후 outputs 백업본도 동기화 권장

---

## 10. 변경 이력 (이번 세션 Task 10~26)

| Task | 변경 |
|---|---|
| 10 | 옵션 C 컬럼 시스템 폐기 + 신규 컨셉 자유 입력바 |
| 11 | 생성 모드 버튼 분리 + 전체 초기화 |
| 12 | buildCopyPrompt 강화 (brand voice + 반복금지 + 길이분포 + 우수사례) |
| 13 | buildCopyPrompt 출력 JSON → 표 + 자가검증 |
| 14 | buildImagePrompt 강화 (라이브러리 디자인 코드) |
| 15 | Apps Script Apify 함수 + 시트 저장 |
| 16 | generator.html 🎯 벤치마크 탭 신설 |
| 17 | buildCopyPrompt/buildImagePrompt 벤치마크 reference 박기 |
| 18 | 벤치마크 시트 → library 자동 import + 🎯 배지 |
| 19 | 벤치마크 라이브러리 확인·삭제 UI |
| 20 | 시트 메뉴 정리 (사용자 도구 → generator로 이동) |
| 21 | 이 통합 가이드 |
| 22 | 메타 비율 변환 섹션 (1:1 → 4:5/9:16/1.91:1) |
| 23 | 카테고리 9개로 교체 (휴대폰/유심만/알뜰폰/중고폰/키즈폰/효도폰/공짜폰/인터넷/인터넷+TV) |
| 24 | 신규 컨셉 + USP 한 줄 반반 배치 |
| 25 | 추가 키워드 폐기 + 감정·톤 통합(9개) + 4그룹 카드 |
| 26 | 디자인 리팩 시작 전 백업 + 가이드 |
| 27 | [A-1] CSS 블록 통째 재작성 (Apple HIG 톤, CSS 변수, 시스템 컬러) |
| 28 | [A-2a] Pretendard 한글 폰트 추가 (iOS 한글 톤) |
| 29 | [A-2b] 폼 박스 구조 단순화 (4그룹 카드 → form-group 구분선) |
| 30 | [B-6] 카피 생성 버튼 통일 (인라인 제거, btn-large + btn-text + btn-caption) |
| 31 | [B-4] 입력 가이드 테이블 simplification (이모지 줄임, 약어 라·롬·이·슬) |
| 32 | [C-3] 마이크로 인터랙션 (fadeIn / slideUp / scaleIn + stagger + prefers-reduced-motion) |
| 33 | [C-4] 디자인 시스템 추출 (styles.html 분리 + include 패턴) — ⚠️ 폐기 (2026-06-12) |
| 36 | [기능 A] fillSlots 정규식 한글 지원 (`\w` → `[^\}]+`) |
| 37 | [기능 B] 검증/벤치마크 토글 (기본 OFF) |
| 38 | [기능 E] PATTERN_EMOTION 9 톤 정규화 + ctx.tones 다중 매칭 (1매칭 ×3 / 2 ×5 / 3 ×7) |
| 39 | [기능 D] 인터넷·인터넷+TV 패턴 풀 신설 (24개) |
| 40 | [기능 C] 카테고리 필터 + 매칭 ×4 가중치 |
| 41 | styles.html include 패턴 폐기 기록 |
| 42 | **[재설계] 시드 카드 모델** — 20카드 = 톤 1개씩 분배 + 풀 폼 컨텍스트 + seedMeta 박힘 + "방향성 시드" 명명 |
| 43 | **[재재설계, 2026-06-12] 시드 카드 폐기 → 3종 박스 매칭 모델** ★ 종민 안 |
| 44 | **[지역 차원 합류, 2026-06-12] 메타_소재 17열·벤치마크 22열 = 지역 (자유 텍스트), 폼 c-region 인풋, regionMatchScore_ 폴백 매칭** |

### Task 44 상세 (2026-06-12)

**배경**: 폰스팟 전국 확대 예정 + 다른 폰매장 범용 활용 의도. 종민 안 = "지역명을 비입력 시 전국 (지역 고려 X), 입력 시 다른 컬럼처럼 추가 / 자유 텍스트 / 하드코딩 X".

**구조**: 지역 = 카테고리와 별개 차원. 자유 텍스트 (드롭다운 부담 ↓, 매장 신설 자유). 공백=전국 의미.

**시트 컬럼**:
- 메타_소재 Q열 (17) = 지역 — 자유 텍스트
- 벤치마크 V열 (22) = 지역 — 자유 텍스트
- `setupLabelingDropdowns` 가 헤더만 설정 (Task 43 카테고리·후킹 구조 드롭다운과 함께)

**백엔드 (meta-sync.gs)**:
- `getMetaCreativesAsJSON_` row 16→17 + `region: row[16]` 키 추가
- `getBenchmarkForGenerator` row 21→22 + `region: row[21]` 키 추가

**프론트 (generator.html)**:
- 폼 그룹 4 "LLM 강조" 안 `form-stack` 으로 박음 (지역 + 신규 컨셉 가로 배치)
- `c-region` 인풋 + `getCopyContext` 에 `region: (document.getElementById('c-region')?.value || '').trim()`
- `resetAllForm` + 프리셋 로드에 `c-region` 박힘

**매칭 로직 (regionMatchScore_)**:
```javascript
function regionMatchScore_(formRegion, sheetRegion) {
  if (!formRegion) return 2;        // 폼 공백 = 모든 광고 매칭
  if (sheetRegion === formRegion || sheetRegion.includes(formRegion) || formRegion.includes(sheetRegion)) return 2;  // 정확/부분 매칭
  if (!sheetRegion) return 1;        // 시트 공백(=전국) → 폴백
  return 0;                          // 다른 지역 = 제외
}
```
search* 정렬 1차 = `_regionScore` 내림차순 (정확 매칭 우선 → 폴백 → 제외). 2차 = CTR (라이브러리) / score (벤치마크).

**LLM 프롬프트 (buildCopyPrompt)**:
- `regionBlock` 추가, `ctx.region` 있을 때만 박힘
- 메시지: "매장명 박힘 + 카피 일부(40%)에 지역 한정 톤 + 나머지는 전국용"

**UI 매칭 카드**:
- 헤드라인 앞에 region 태그 배지: region 있으면 색상 박스 (📍 광교점), 공백이면 회색 "전국"
- 라이브러리 박스 = 초록 (#34C759), 벤치마크 박스 = 주황 (#FF9500)
- `_regionScore === 1` (폴백 매칭)이면 헤드라인 끝에 "(폴백)" 표시

**library 합류**:
- `importFromMetaJSON`: `region: (item.region || '').trim() || existing?.region || ''`
- `fetchBenchmarkFromSheetIntoLibrary`: `region: bm.region || ''`

**파일 손상 18회째**: Edit 누적 → fallbackCopy 함수 중간 잘림 (3009 < 정상). 백업 `generator.v_2026-06-12_pre-task43.html` 활용 fallbackCopy~끝 복구 + loadGuideThresholds IIFE 재추가. 최종 3087라인 정상.

**자가 검증 결과**:
- 새 함수 정의 9개 확인 (regionMatchScore_ 포함) ✅
- `region` 박힘 27곳 (시트 컬럼·매칭·UI·LLM·라이브러리 합류 전체) ✅
- 시드 카드 함수 흔적 0 ✅
- 파일 끝부분 `</html>` 박힘 ✅

**범용 시스템 단계 메모**: L1 = 시트 복제만 (즉시 가능) / L2 = 카테고리·지역 설정 시트 (Task 44가 그 시작) / L3 = 브랜드 본질 시트로 분리 (`buildCopyPrompt` 안의 폰스팟 USP·도메인·차별점) / L4 = 멀티 테넌트 SaaS. Task 44 = L2 첫 걸음 (지역 차원).

---

### Task 43 상세 (2026-06-12)

**배경**: Task 42의 시드 카드 모델을 종민이 실사용 안 함 확인 ("뭘 폐기한다는건지 이해가안됨" — 본 적 없음 → 활용 안 함). 종민 명령: "새로운 3종 박스만 생성". 활용 가치 없는 톤 다양화 시드 폐기 + 매칭 도구로 전환.

**구조**: 버튼 1개 `광고 카피 가이드 생성` → 결과 3종 박스
- 🤖 일반 LLM 프롬프트 (파란 #007AFF) — 항상 표시. `buildCopyPrompt(ctx)` 그대로 활용.
- ✨ 라이브러리 매칭 (초록 #34C759) — 폼 카테고리 == lib.category + CTR ≥ minCtr (기본 7%).
- 🎯 벤치마크 매칭 (주황 #FF9500) — 폼 카테고리 == bm.category + 운영일 ≥ minDays (기본 90) + score ≥ minScore (기본 3).

**시트 라벨링 (종민 수기)**:
- 메타_소재 시트 16열 = `카테고리` (드롭다운 9개)
- 벤치마크_경쟁사_광고 시트 20열 = `카테고리` / 21열 = `후킹 구조` (드롭다운 8개: 질문형/단언형/비교형/한정형/가격강조/감성·공감/위협형/FOMO형)
- 라벨링 안 하면 매칭 영구 0건 = 일반 박스만 표시.

**백엔드 (meta-sync.gs)**:
- `getMetaCreativesAsJSON_`: row 15→16, `category: row[15]` 추가.
- `getBenchmarkForGenerator`: row 19→21, `category: row[1]` (BM/CP 구분자) → `kind`로 키 변경, 신규 `category: row[19]` + `hookStructure: row[20]`.
- 메타_소재 1~15열만 setValues / 벤치마크 1~19열만 appendRow → 16/20/21열 자동 덮어쓰기 영구 안전 (코드 보호 불필요).

**프론트 (generator.html)**:
- 신규 함수: `generateAdCopyGuide` / `searchLibraryMatching` / `searchBenchmarkMatching` / `buildLibraryEnrichedPrompt` / `buildBenchmarkEnrichedPrompt` / `renderAdCopyGuide` / `copyGeneralPrompt` / `copyLibraryPrompt` / `copyBenchmarkPrompt`.
- 폐기: `generateCopiesTemplate` / `renderCopies` (시드 카드 모델 전체).
- 폴백: `generateCopiesFromLibrary` / `generateCopiesViaLLM` / `generateCopies` → 모두 `generateAdCopyGuide` 호출 (옛 호출지 안전).
- `fetchBenchmarkFromSheetIntoLibrary` library 합류 시 `kind` 키 추가 + `category` / `hookStructure` 박힘.
- `importFromMetaJSON` 측 `category: item.category || existing?.category || ''` 우선순위 (시트 16열 라벨 우선).

**UI**:
- `.result-box` + `.result-general/library/benchmark` 색상 분기 + `.match-card` + `.match-empty`.
- 박스 헤더에 슬라이더 (input type=number) 인라인 박힘 + change 시 `renderAdCopyGuide` 재호출 + localStorage 저장.
- localStorage 키: `gen.minCtr` / `gen.minDays` / `gen.minGrade`. 페이지 로드 시 IIFE 복원.

**벤치마크 컨텍스트 다름 처리**: 카피 자체 복제 X. `hookStructure` 컬럼 빈도 집계 → "빈출 후킹 구조: 질문형(×3) / 가격강조(×2)" 형식 LLM 프롬프트에 박힘. 광고 자체는 `[페이지명] N일 운영 / 등급 / 후킹: X` 메타만 reference 박힘. "경쟁사 가격·상품·매장 정책은 폰스팟과 다름 → 후킹 구조만 흡수" 명시.

**파일 손상 17회째**: Edit 누적으로 fallbackCopy 함수 중간에서 끝부분 잘림. 백업 `generator.v_2026-06-12_pre-task43.html` (2961라인) 활용 fallbackCopy~끝 복구 + loadGuideThresholds IIFE 재추가. 최종 3036라인 정상 (`</script></body></html>` 박힘). **다음 큰 변경은 통째 Write 권장** (재차 강조).

**자가 검증 결과**: 
- 새 함수 9개 정의 확인 ✅
- `generateCopiesTemplate` 정의·호출 흔적 0건 ✅
- `generateAdCopyGuide()` 호출 5곳 (버튼·toggle·폴백 3개) ✅
- 파일 끝부분 `</html>` 박힘 ✅

---

## 11. 디자인 리팩 시작 전 스냅샷 (2026-06-09)

> Task 26에서 박음. 디자인 리팩(애플 톤 변환) 시작 전 현재 작동하는 상태 백업.
> 백업 파일: `ads/code/apps_script/generator.v_2026-06-09_pre-design-refactor.html`

### 11-1. 카피 입력 폼 구조 (Task 25 완료 후)

```
📖 입력 가이드 (접기/펼치기)
└─ 테이블 (분류·타겟 / 컨텍스트 / 카피메시지 / LLM강조 그룹별)
   반영처 열: 📚 라이브러리 / 🤖 LLM / 🎨 이미지 / 📋 슬로건

카피 입력 폼
├─ 📋 분류 + 타겟 (grid-3 카드)
│   ├─ 카테고리 (9개: 휴대폰/유심만/알뜰폰/중고폰/키즈폰/효도폰/공짜폰/인터넷/인터넷+TV)
│   ├─ 타겟 연령 (10대~50대+/전 연령)
│   └─ 타겟 성별 (여성/남성/전체)
│
├─ 🎯 컨텍스트 (grid-3 카드)
│   ├─ 시즌/이벤트 (시즌리스/봄/여름/추석/블프/신학기 등 10개)
│   ├─ 제품 (구체적, 자유 입력)
│   └─ 길이 선호 (짧게/중간/길게/자유)
│
├─ 💬 카피 메시지 (카드)
│   ├─ 💡 핵심 USP (한 줄, 템플릿 {USP} 슬롯 + LLM 반영)
│   └─ 📢 톤·감정 (다중 9개)
│      ☐ 감성/공감 ☐ 직설/강력 ☐ 유머 ☐ 정보성/신뢰 ☐ 프리미엄
│      ☐ 호기심 ☐ 긴급/FOMO ☐ 손실회피 ☐ 자부심
│
└─ 🆕 신규 컨셉 (LLM 강조 — 노란 배경 카드)
    추상 키워드, 자유 입력, 템플릿 반영 ❌
```

### 11-2. 생성 모드 버튼 4개 (그룹 직하)

- 📚 라이브러리 + 벤치마크 기반 생성 (즉시 20개)
- 🤖 LLM 프롬프트 생성 (Claude/GPT 챗용)
- 🎲 랜덤 채우기
- 🧹 전체 초기화

### 11-3. 카피 결과 영역 위 비율 변환 (Task 22)

🔄 메타 비율 변환 (1:1 → 4:5/9:16/1.91:1)

### 11-4. 폐기된 폼 요소 (호환성 위해 코드 잔존)

- ❌ 강조 감정 단일 드롭다운 → 톤·감정 다중 체크박스에 흡수
- ❌ 추가 키워드 input → 폐기 (라이브러리 우수 키워드 자동주입은 신규 컨셉 비었을 때로 이동)
- ctx.emotion = '자유' / ctx.keywords = '' 더미 박혀있음 (fillSlots 폴백 호환)

### 11-5. 탭 4개

📝 카피 생성 / 📚 라이브러리 / 🎯 벤치마크 / ⚙ 설정

### 11-6. 핵심 함수 인덱스 (Task 25 후)

| 함수 | 위치 |
|---|---|
| getCopyContext | ~1300 |
| randomFillCopy | ~1316 |
| resetAllForm | ~1334 |
| generateCopiesFromLibrary | ~1075 |
| generateCopiesViaLLM | ~1095 |
| generateCopiesTemplate | ~1430 |
| getMetaLibraryInsights | ~1100 |
| buildCopyPrompt | ~1539 |
| buildSloganVariationPrompt | ~1680 |
| buildImagePrompt | ~1900 |
| analyzeWinningDesigns_ / buildLibraryDesignBlock_ | ~1456 |
| buildBenchmarkDesignBlock_ | ~1516 |
| searchBenchmark / loadBenchmarkFromSheet | ~818, ~857 |
| renderBenchmarkResults | ~970 |
| deleteBenchmarkOne / Selected | ~925, ~951 |
| fetchBenchmarkFromSheetIntoLibrary | ~2118 |
| copyResizePrompt | ~884 |

### 11-7. 디자인 리팩 계획 (Task 27~)

A 우선순위 (먼저):
1. **CSS style 블록 통째 재작성** (애플 톤: System Gray + 단일 액센트)
2. **카피 폼 4그룹 카드 인라인 → 클래스화**
3. **카피 결과 카드 + 배지 통일**

B 우선순위 (다음):
4. 입력 가이드 테이블 simplification
5. 탭 디자인 segmented control
6. 버튼 통일 (primary/secondary/danger)
7. 벤치마크 카드 정리

각 단계별 종민 확인 후 다음 진행.

### 11-8. 복구 명령 (디자인 변경 중 손상 시)

```bash
cp ads/code/apps_script/generator.v_2026-06-09_pre-design-refactor.html ads/code/apps_script/generator.html
```

이 한 줄로 Task 25 완료 직후 상태로 즉시 복구.

---

## 12. 디자인 리팩 완료 (Task 27~33)

### 12-1. 적용된 디자인 토큰 (Apple HIG light)

```
컬러 시스템:
  --system-bg: #F2F2F7         (전체 배경)
  --card-bg: #FFFFFF           (카드)
  --secondary-bg: #F2F2F7      (입력 배경)
  --label: #1D1D1F             (본문)
  --label-tertiary: #86868B    (보조)
  --separator: rgba(60,60,67,0.12)
  --accent: #007AFF            (시스템 블루)
  --success: #34C759, --warning: #FF9500, --danger: #FF3B30

폰트:
  Pretendard (한글) > -apple-system > Apple SD Gothic Neo > SF Pro > system-ui
  letter-spacing: -0.2px

Radius: 6/10/14/18
Shadow: subtle (0 1px 2px + 0.5px outline)
Transition: 150ms cubic-bezier(0.4, 0, 0.2, 1)
```

### 12-2. iOS 톤 적용 요소

- 탭 = segmented control (둥근 chip)
- 입력 필드 = 보더 없음 + 회색 배경 + focus 액센트 ring
- 체크박스/라디오 = pill chip (선택 시 액센트 배경)
- 버튼 = primary 액센트 + active scale(0.98)
- 카드 = subtle border + shadow
- selection-bar = backdrop-filter blur(20px) (frosted glass)
- 스크롤바 = subtle gray pill
- 폼 그룹 = 큰 카드 1개 + 미묘한 구분선 (form-group)
- 마이크로 인터랙션 = fade/scale/slide + stagger 카피 카드 + prefers-reduced-motion 존중

### 12-3. styles.html include 패턴 — ⚠️ 폐기 (2026-06-12)

**이전 설계 (의도)**:
```
Code.gs:
  function include(filename) { return HtmlService.createHtmlOutputFromFile(filename).getContent(); }
  doGet: createTemplateFromFile + evaluate()

generator.html: <?!= include('styles') ?>
```

**실제 적용 결과 — 폐기**:
- styles 파일 추가가 종민 운영 흐름에 부담 (Apps Script 에디터 새 파일 추가 + 통째 붙여넣기)
- `<?!= include('styles') ?>` 호출 시 styles 파일 없으면 **`Exception: styles(이)라는 이름의 HTML 파일을 찾을 수 없습니다`** 에러
- 종민 결정 (2026-06-12): generator.html에서 `<?!= include('styles') ?>` 라인 통째 제거 → 옛 `<style>` 블록 그대로 사용
- 백업본 (`ads/code/apps_script/generator.html`)에서도 제거 완료

**다음 클로드 세션 주의**:
- `<?!= include(...) ?>` 패턴 사용하려면 **반드시 동시에**:
  1. Apps Script 프로젝트에 해당 HTML 파일 존재
  2. `Code.gs`에 `include()` 함수 정의
  3. `doGet`이 `createTemplateFromFile + evaluate()` 사용 (단순 `createHtmlOutputFromFile`은 scriptlet 작동 X)
- 셋 중 하나라도 빠지면 즉시 깨짐. **단일 페이지 운영 시 권장 X.**
- 다른 브랜드 페이지(generator_internet 등) 만들 시점에 styles 분리 재검토 (그땐 같은 디자인 재사용 가치 명확).

**현재 상태**:
- generator.html: 옛 `<style>` 블록 (line 7~) 그대로 살아있음. styles 분리 X.
- `styles.html` 파일은 `ads/code/apps_script/` 폴더에 남아있지만 **사용 안 함** (참고용).
- Code.gs `include()` 함수 + `createTemplateFromFile`은 그대로 (다음에 다시 활용 가능).

### 12-4. 폼 최종 구조 (디자인 리팩 후)

```
section "카피 입력 폼"
├── form-group "분류 · 타겟"
│   └── grid-3 (카테고리 9개 / 연령 / 성별)
├── form-group "컨텍스트"
│   └── grid-3 (시즌 / 제품 / 길이)
├── form-group "카피 메시지"
│   ├── 핵심 USP input
│   └── 톤·감정 체크박스 9개 (chip)
└── form-group--accent "LLM 강조"
    └── 신규 컨셉 input

[btn-row]
  📚 라이브러리 · 벤치마크 기반 (btn-large primary)
  🤖 LLM 프롬프트 (btn-large secondary)
[btn-caption] 라이브러리/LLM 차이 안내
[btn-row]
  🎲 랜덤 채우기 (secondary small)
  전체 초기화 (btn-text small)
```

---

## 13. 이번 세션 총 결산

- 완료 Task: **34개** (Task 1~7, 10~33)
- 파일 손상 → 백업본 복구: **16회**
- 신규 파일: **5개**
  - `ads/data/seed_concept_tags.md`
  - `_docs/APIFY_INTEGRATION_GUIDE.md`
  - `ads/IMPLEMENTATION_GUIDE_2026-06-09.md`
  - `ads/code/apps_script/styles.html`
  - `ads/code/apps_script/generator.v_2026-06-09_pre-design-refactor.html` (백업)

### 핵심 기능

| 영역 | 결과 |
|---|---|
| 카피 생성 | 라이브러리(템플릿) + LLM 2개 모드, brand voice 강화, 단어 반복 ≤3회 + 길이 분포 강제 + 자가검증, 출력 마크다운 표 |
| 이미지 프롬프트 | 라이브러리 + 벤치마크 디자인 코드 자동 분석 + 박힘 |
| 비율 변환 | 1:1 → 4:5/9:16/1.91:1 한글 재구성 프롬프트 |
| 벤치마크 | Apify Meta Ad Library 자동 수집, 시트 저장, 자동 import, 카피·이미지 reference, 등급별 ★ |
| 라이브러리 | 메타_소재 시트 자동 동기화, 우수 등급 자동, 검증 헤드라인 카피 후보 |
| UI | Apple HIG + Pretendard, 4 form-group, 9개 톤·감정 chip, 신규 컨셉 자유 입력, 폼 4그룹 → 큰 카드 1개 |
| 디자인 시스템 | styles.html 분리 (다른 브랜드 페이지 재사용 가능) |

---

## 14. 작업 후보 (클로드가 종민 명령 받았을 때 매칭)

### 종민이 "토큰 보안" / "재발급" 류 명령 →
- Apps Script Properties `APIFY_TOKEN` 교체 안내
- 또는 자동 재발급 코드 작성

### 종민이 "트리거" / "자동" / "주간 수집" 류 →
1. **벤치마크 운영일수 자동 갱신** — `meta-sync.gs`에 `refreshBenchmarkDays()` + 매일 01:50 트리거
2. **Apify 주간 자동 수집** — 시트 `Apify_키워드` 신설 + 매주 월요일 03:00 트리거, 시트 키워드 5개 순회

### 종민이 "인터넷" / "확장" / "다른 브랜드" 류 →
- **B 방식 (별도 페이지)**: `generator_internet.html` 신설 (styles.html include로 디자인 재사용)
  - brand voice 박기 (결합·위약금·사은품·속도·견적)
  - `meta-sync.gs` `SpreadsheetApp.getActive()` → `openById(SHEET_ID_INTERNET)` 동적
  - Properties에 `SHEET_ID_INTERNET` / `META_TOKEN_INTERNET`
  - `Code.gs doGet`에 `?page=internet` 라우팅 추가
- **5개 미만**: B 유지 (별도 페이지)
- **6개 이상으로 늘면**: C (시트 `브랜드_설정` 탭 + URL 파라미터 동적) 전환 권장

### 종민이 "비전" / "이미지 분석" 류 →
- Apify 썸네일 URL → Claude Vision / GPT-4o Vision 호출 (광고당 ≈ $0.005)
- `meta-sync.gs`에 `analyzeBenchmarkVision_(thumbnailUrl)` 추가
- 결과 시트 컬럼 추가 (색상·구도·typography 추출)

### 종민이 "부사수" / "텔레그램" / "인계" 류 →
- 카피 픽 + 이미지 프롬프트 → 텔레그램 봇으로 자동 전송
- `automation/scripts/tg_send.py` 패턴 재사용

### 종민이 "LLM 자동" / "챗 안 돌리고" 류 →
- buildCopyPrompt 결과 → Claude/OpenAI API 직접 호출 (수동 챗 → 자동)
- 비용·셋업 부담 안내 (월 $5~50)

### 종민이 "다크 모드" / "모바일" 류 →
- `styles.html`에 `@media (prefers-color-scheme: dark)` 토큰 추가
- 또는 `@media (max-width: 768px) { .grid-3 { grid-template-columns: 1fr; } }` 등

### 종민이 "옛 style 제거" / "C-4 완성" 류 → ⚠️ 폐기됨 (2026-06-12)
- styles.html include 패턴은 **종민이 직접 폐기 결정**
- 옛 `<style>` 블록이 단일 진실의 원천
- 다른 브랜드 페이지(generator_internet) 만들 시점에 다시 검토

---

## 15. 다음 세션 첫 진입 절차 (클로드 액션)

1. **이 가이드 §10 + §13 결산** — 현재 시스템 상태 1분에 파악
2. **§6 함수 인덱스** — 코드 위치 파악
3. **§12 디자인 토큰 + `styles.html`** — 디자인 시스템 파악
4. **종민 명령 받음 → §14 매칭** → 작업 시작
5. 코드 변경 시 **§16 파일 손상 회피 룰 준수**

---

## 16. 파일 손상 회피 룰 (이번 세션 16회 손상에서 학습)

### 패턴
- generator.html 큰 Edit 누적 시 끝부분 잘림 (특히 한글·이모지 다수 텍스트)
- 한 세션에서 8회 Edit 넘으면 손상 확률 ↑

### 회피
1. **큰 변경 = 통째 Write** (Edit 누적 X)
2. **검증 매번**: Edit 후 `LC_ALL=C grep -ac "</html>"` 확인 → 0이면 즉시 복구
3. **백업본 항상 보존**: `outputs/phonespot/ads/generator.html` 또는 `generator.v_YYYY-MM-DD_xxx.html`
4. **복구 명령** (스크립트화 권장):
   ```bash
   LAST_FN=$(LC_ALL=C grep -an "^function" generator.html | tail -1 | awk -F'function ' '{print $2}' | awk -F'[ (]' '{print $1}')
   BACKUP=/path/to/backup
   CUR_LINE=$(LC_ALL=C grep -an "^function $LAST_FN" generator.html | tail -1 | cut -d: -f1)
   BACKUP_LINE=$(LC_ALL=C grep -an "^function $LAST_FN" $BACKUP | head -1 | cut -d: -f1)
   head -n $((CUR_LINE - 1)) generator.html > new
   tail -n +$BACKUP_LINE $BACKUP >> new
   mv new generator.html
   ```

### Apps Script V8 호환성
- `??=` `||=` `&&=` (logical assignment, ES2021) **미지원** → 전통 패턴 (`if (!x) x = ...`) 사용
- `?.` (optional chaining, ES2020) 지원
- `??` (nullish coalescing) 지원
- `async/await` 지원
