# TASK_LAUNCHERS — 기능별 새 task 호출 지시문

> 새 Cowork/Claude task를 이 폴더(`C:\backup\phonespot_cardnews`)에 연결한 뒤 **아래 블록을 그대로 붙여넣으면** 해당 기능으로 바로 진입한다.
> 모든 task는 진입 시 `CLAUDE.md`를 자동 부트스트랩(STEP 1 가이드 Read → STEP 2 라우팅)하므로, 지시문은 짧아도 형식·룰이 자동 적용된다.
> `[ ]` 부분만 상황에 맞게 채우면 됨.

---

## ① 폰스팟 광고 대장 시트 관리

```
폰스팟 광고운영 task. CLAUDE.md STEP 0·STEP 1 적용하고 ads/README_FOR_AI.md → ads/MANUAL.md 진입.
할 일: [전체 새로고침 / 메타·네이버·당근·인스타 동기화 / KPI·매트릭스 갱신 / 광고그룹 추이 / 미매핑 UTM 정리].
규칙: 코드 수정은 SYSTEM_MAP G단원만 읽고 고침. apps_script/ 는 git push → GitHub Actions가 clasp --force 배포 →
콘솔 직접 수정 ❌. 시트 read 필요하면 apps_script_sheet_export / Drive snapshot(B1) 사용.
```

## ② 카드뉴스 주제 수집 & 카드뉴스 생성

```
카드뉴스 task. CLAUDE.md STEP 1 공통 6개 + 인사이트 시트 2개(유튜브_인사이트·메타_인사이트) Read.
명령: "신규 수집" = 인사이트 가중치 + 채널 운영 시트 7일 스캔 + cardnews/articles/ Glob 중복 회피 +
4라인 병렬 WebSearch → 후보 표(가중치 라벨). "N번 발행" = CARDNEWS_BUILD.md 워크플로로 기사 JSON +
prompt.md + outbox 신호. 캡션·후킹은 caption_template.md 5채널 룰.
이번 요청: [수집 / N번 발행 / 프롬프트 다듬기].
```

## ③ 카드뉴스 영상 생성 (패널 사용)

```
카드뉴스 영상 task. _docs/INSTRUCTIONS_SHORTS.md Read.
패널 = CODEX_VIDEO_DESK/dashboard/server.py (실행 = 00_PHONE_SPOT_PANEL.bat). 빌드 = shorts/run_codex_casual.bat
(또는 패널의 셀렉트 렌더). casual/newsroom 결.
수정 시: 의미매칭·일러스트·포토 = SYSTEM_MAP E단원 / 영상 연출·자막·커버 = C단원. 대형 파일은 Edit 금지·bash-python(I단원).
이번 요청: [기사 슬러그 NNN 영상 빌드 / 매칭 디버깅 / 연출 수정].
```

## ④ 영상 생성 (타이포그래피)

```
타이포 홍보영상 task. shorts/promo/README.md + shorts/promo/GUIDE_TYPOGRAPHY.md Read → shorts/run_promo.bat
(여러 건 = run_promo_batch.bat). 카드뉴스 영상과 다른 결: 타이포/모션그래픽, 나레이션 없음, 효과음+음악(스타일별 SFX·무드 음악풀).
이번 요청: [홍보 컨셉/문구 = ____ 로 promo 1편 빌드].
```

## ⑤ 영상 생성 — AI 실사 (Higgsfield)

```
실사 AI 광고 task. shorts/promo_ai/README.md + shorts/promo_ai/WORKFLOW.md Read.
Higgsfield MCP 호출 (Kling 3.0 1순위 / Seedance 2순위) → ffmpeg 합치기. 15초 9:16.
★ 시작 전 결제 상태 + balance 점검 필수(크레딧 부족하면 중단). 이미지→영상 클립 생성 후 ffmpeg concat.
이번 요청: [광교점 실사 / 제품 = ____ / 컨셉 = ____ 15초 광고].
```

## ⑥ SNS 크롤링 (Apify 경쟁사 광고 벤치마크)

```
SNS 크롤링(경쟁사 광고 벤치마크) task. _docs/APIFY_INTEGRATION_GUIDE.md Read.
진입 = generator.html(Web App) 🎯 벤치마크 탭 (🔍 Apify 검색 → 선택 → 💾 시트 저장 → T/U/V 라벨링).
코드 = apps_script/meta-sync.js 라인 935~ (fetchBenchmarkFromApify_ / saveBenchmarkToSheet_ / searchBenchmarkViaApify).
Actor curious_coder/facebook-ads-library-scraper ($0.00075/광고), 토큰 = PropertiesService APIFY_TOKEN, 시트 = 벤치마크_경쟁사_광고.
이번 요청: [키워드 = ____ 로 KR 광고 N건 수집 / 코드 수정 / 라벨링].
```

## ⑦ 광고 카피·이미지 생성기 (generator.html) — 이어작업

```
광고 생성기 이어작업 task. 정본 = ads/IMPLEMENTATION_GUIDE_2026-06-09.md.
★ 읽는 순서: §0-1 "최신 아키텍처(2026-06-12 세션2)" 먼저 (이게 현재 상태, §2~6은 일부 구버전) →
§5 함수 인덱스 → §6 프롬프트. 변경 상세 + 알려진 함정 = CLAUDE.md STEP 8 "2026-06-12 (세션 2)".
대상 파일: apps_script/generator.html(대형 ~2,863줄) + apps_script/meta-sync.js + Code.js + style.html.

[현재 구조] generator 4탭: 📝카피 / 📚라이브러리 / 🎯벤치마크 / ⚙설정.
결과 3종 = 🎲8행 랜덤변주(1순위) → ✨라이브러리 추천 → 🎯벤치마크 추천. 1:1 매핑(변주=참고없음 / 라이브러리=라이브러리만 / 벤치마크=벤치마크만).
라이브러리 탭 함수: saveToLibrary → library[] 자동채번 → pushLibraryToSheet → (Apps Script) pushLibraryFromGenerator → 시트 '광고_라이브러리'.
exportLibrary/importLibrary(JSON 백업), clearLibrary, library-filter 검색.
의미매칭: getSemanticAdMatches(meta-sync.js, Gemini) — 컨셉/지역 앵글 주제유사도, 임계 55, GEMINI_API_KEY + 배포 웹앱 필요(외부 URL 모드면 스킵).

[명시된 보류(=이어할 후보)] ① 컨셉_뱅크: 신규컨셉 시트 저장 ② 코어 완전 hard-lock ③ 범용화 L2(Task 44, 지역 차원 = 카테고리·지역 설정 시트) → L3 브랜드 본질 시트 분리 → L4 멀티테넌트.

[주의] generator.html 수정은 통째 Write 권장(대형 = Edit truncation 위험). 수정 후 Web App 재배포 + 종민 콘솔 검증.
배포 = apps_script/ git push → GitHub Actions clasp --force 자동. 콘솔 직접 수정 ❌(다음 push에 덮어씀).
APIFY_TOKEN·GEMINI_API_KEY = PropertiesService(클라우드, PC 이식 무관).

이번 요청: [보류 ①컨셉_뱅크 구현 / ②코어 hard-lock / ③L2 지역설정 시트 / 라이브러리 탭 ____ 기능 추가 / 버그 ____].
```

---

## 추가 트랙 (목록 외, 필요 시)

| 기능 | 호출 한 줄 |
|---|---|
| KT다이렉트샵 광고운영 | `KT 광고운영 task. ads_kt/README_FOR_AI.md 진입. 폰스팟과 별도 시트.` |
| 멀티 브랜드 셋업 | `멀티 브랜드 task. ads/MULTI_BRAND_ARCHITECTURE.md 읽고 Phase [N] 진행. 광고운영 task와 분리(별도 task 결정).` |
| 시트 read / 스냅샷 | `시트 read task. apps_script_sheet_export + Drive 폴더 "PhoneSpot Sheet Snapshots"(매일 03:00 JSON). 큰 탭은 __headers.json 사용.` |
| 재해 복구 / 키 재발급 | `복구 task. _docs/DISASTER_RECOVERY.md 진입. 키 손실 = 재발급 절차(PropertiesService 키는 Google 클라우드라 무영향).` |

---

## 공통 주의 (모든 task)

- 산출물은 표준 폴더(`cardnews/articles·images·output`, `shorts/`, 시트)에만. 임의 위치 1회성 파일 ❌.
- "가이드 박아" = 새 요약본 만들지 말고 `_docs/SYSTEM_MAP.md` 해당 대단원 + CLAUDE.md STEP 8에 사실만 1줄.
- 같은 PC에서 ①·②·③ 동시 task 가능(영역 분리 `apps_script/` vs `cardnews/` vs `shorts/` = git 충돌 거의 0).
- 이 PC = `C:\backup\phonespot_cardnews`, 사용자 `313jo`, venv `.phonespot_runtime`(윈도우 인증서 truststore 주입됨).

---

변경 이력
- 2026-06-18: 신설. 6개 기능 + 추가 트랙 5개 호출 지시문. PC 이식(STEP 8 2026-06-18) 직후 작성.
