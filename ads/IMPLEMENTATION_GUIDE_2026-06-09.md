# 폰스팟 광고 자동화 — 2026-06-09 통합 적용 가이드

> 이번 세션(2026-06-09) 변경사항을 한 문서에 정리. 다음 세션 진입 시 이 문서로 현재 상태 즉시 파악.
> 마지막 갱신: 2026-06-09

---

## 0. 한 줄 요약

**시트 = 데이터 저장소 + 자동화 백엔드 / generator.html(Web App) = 사용자 도구 통합.**
- 시트 메뉴(📡 메타 자동화) = 매일 자동 동기화 + 트리거 + 토큰 테스트만 (운영자가 시트에서 다루는 자동화)
- generator.html = 카피 생성 + 슬로건 변형 + 이미지 프롬프트 + **🎯 Apify 벤치마크 수집/관리** + 라이브러리

---

## 1. 셋업 순서 (종민 1회만, 약 10분)

### 1-1. Apify 계정 + 토큰
1. https://apify.com 가입 (Google 로그인 가능)
2. Settings → Integrations → API tokens → Create new token → 복사
3. (안전) 토큰 노출되면 같은 페이지에서 Regenerate

### 1-2. Apps Script Properties에 토큰 저장
1. 시트 → 확장 프로그램 → Apps Script
2. ⚙ 프로젝트 설정 → 스크립트 속성 → 속성 추가:
   - 키: `APIFY_TOKEN`
   - 값: (Apify 토큰)
   - 저장

### 1-3. 코드 배포
1. `meta-sync.gs` 전체 복사 → Apps Script 에디터 교체 → 저장
2. `generator.html` 전체 복사 → Apps Script 에디터 교체 → 저장
3. (Code.gs에 `doGet` 함수 살아있는지 확인 — 없으면 추가, 별도 가이드 §5)
4. 배포 → 배포 관리 → ✏️ 편집 → 새 버전 → 배포
5. 시트 새로고침 (F5) → 📡 메타 자동화 메뉴 확인

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

## 10. 변경 이력 (이번 세션 Task 10~21)

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
