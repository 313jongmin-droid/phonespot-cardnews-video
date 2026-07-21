# 폰스팟 카드뉴스·영상 프로젝트 — 클로드 부트스트랩

> **새 클로드 세션이 이 폴더를 열면 가장 먼저 이 파일을 읽음.**
> 모든 가이드·매뉴얼·매커니즘 진입점은 여기. 다른 세션과 같은 공식으로 작업하려면 **아래 STEP 1을 반드시 먼저 실행**.
>
> **이 폴더에 들어온 모든 task는 이 하네스 구조를 그대로 이어받는다.** 임의 위치에 1회성 요약본을 만들지 않는다.
> 구조 = ① 헤드(CLAUDE.md, 진입·라우팅) → ② `_docs/SYSTEM_MAP.md`(대단원 A~J 개발 맵, 수정 인덱스)
> → ③ 각 대단원 마스터 가이드. 작업·문서화 모두 이 3층 안에서만.

---

## ★ 문서화 규약 — "가이드 박아" 명령 처리법 (최우선, 항상 적용)

사장님이 **"가이드 박아 / 가이드에 넣어 / 문서화해 / 기록해"** 라고 하면 (직전 설명을 다시 안 해도)
**아래 절차로 기존 구조에 합류시킨다. 절대 아무 데나 새 요약본·1회성 md 생성 ❌.**

1. **대상 대단원 식별** — 방금 한 작업이 `_docs/SYSTEM_MAP.md` 0번 인덱스의 어느 대단원(A~J)인지 정한다.
2. **그 대단원 섹션을 갱신** — 경로·핵심 함수·"수정 시 읽을 것"·**함정**에 이번 변경/사실을 박는다(기존 항목 옆에 추가, 통째 교체 X).
3. **SYSTEM_MAP 변경이력 1줄** — 파일 맨 끝 "변경 이력"에 날짜+요약 1줄.
4. **라우팅이 바뀌었으면 헤드(CLAUDE.md)도 갱신** — 새 진입점/명령 패턴/파일이면 STEP 1·2·4 동기화.
5. **CLAUDE.md STEP 8 변경이력 1줄** — 하네스 차원 변경(새 가이드/명령/구조)일 때만.
6. **새 대단원이 필요하면** SYSTEM_MAP에 단원을 신설하고 0번 인덱스 표에 등록(없는 분류를 억지로 끼우지 말 것).

원칙: **사실만 박는다**(추측·미사여구 X). 경로는 리포 루트 상대경로. 줄번호는 검증된 것만.
새 task·다른 task가 들어와도 이 규약과 SYSTEM_MAP만 읽으면 같은 공식으로 이어받는다.

---

## STEP 0 — 머신 역할 & 업데이트 적용 (★ 최우선 전제, 2026-06-08 / 2026-06-15 갱신)

네 역할로 고정. **모든 해결책은 이 구조 안에서만** 준다.

| 머신 | 역할 | git |
|---|---|---|
| **로컬 PC** (사무실, `C:\backup\phonespot_cardnews`) | **개발/편집/운영 단일 작업 머신**. 모든 task(광고운영·카드뉴스·영상·기사·.bat) 여기서 수정 → commit → push. 영역 분리 = `apps_script/`(광고운영) / `cardnews/·_docs/`(카드뉴스) / `shorts/·CODEX_VIDEO_DESK/`(영상) → 충돌 거의 0 | **push only** |
| **노트북** | 크롬 원격 입구만. 사무실 못 갈 때 로컬 PC 조종용. **직접 작업·git 수정 ❌** | — |
| **부사수 PC** (`C:\PhoneSpot\phonespot_cardnews`) | 카드뉴스·영상·패널 렌더링 전용 단독 생산기 | **pull only** |
| 메인 PC (`192.168.0.7`) | 카드 이미지 원본 자산 소스(git 비공유 자산 LAN sync 출처) | — |

### 원칙
1. 해결 = **로컬 PC 수정 → push → 부사수 PC pull → 부사수 PC에서 실행.** 로컬 PC 실행 결과 신뢰 ❌(렌더링 검증은 부사수 PC 로그).
2. **부사수 PC는 pull only.** 패널 "GitHub 업로드"(`codex_github_upload`)·자동커밋을 부사수 PC에서 쓰면 origin/main 분기 → pull 충돌. **push는 로컬 PC에서만.** ※ `_docs/DEV_LAPTOP_OFFICE_RUN_GITHUB.md`의 "사무실도 push" 모델은 **폐기**(이 STEP 0이 우선).
3. **git 전파 vs 비전파**(STEP 7 위생 연동): 전파=코드·`.bat/.ps1/.mjs`·`cardnews/articles/*.json`·가이드·`.gitattributes` / 비전파(셋업·LAN sync·Drive로 따로)=`cardnews/images`·`output`·`_secrets`·`node_modules`·`.playwright`·임베딩 1GB·`library_share_path.txt`.
4. 렌더링 진단은 부사수 PC 로그 기준(로컬 PC에서 못 봄). 광고운영 동기화 진단은 Apps Script 콘솔 로그.
5. **다른 task 충돌**: 같은 로컬 PC 안에서 광고운영 클로드 + 카드뉴스 클로드 동시 작업 가능. 영역 별개라 git 충돌 거의 0. 단 같은 파일 동시 수정은 회피 (책임 분담 표 = `ads/MULTI_BRAND_ARCHITECTURE.md`).
6. **★ 카드뉴스 repo 내부 3-task 분할 (2026-06-24 종민 결정)**: ① **패널 엔진** = `CODEX_VIDEO_DESK/PANEL_TASK.md`(dashboard·worker·큐) ② **영상 제작** = `shorts/RENDER_TASK.md`(cardnews·shorts 콘텐츠·렌더) ③ **주제 엔진** = `_docs/TOPIC_ENGINE.md`(**별도 task가 관리** — 패널·제작 task는 TOPIC_ENGINE/TOPIC_TO_PROMO 편집 ❌). 같은 monorepo·폴더 이동 ❌, **소유권+계약만 분리**(멀티PC 원클릭/pull 모델 보존). 계약 P↔R = `run_<track>.bat <인자>` + 결과 `RESULTS/<slug>_<track>/`. 시작: "패널 task 시작 = PANEL_TASK.md 읽고 dashboard만" / "제작 task 시작 = RENDER_TASK.md 읽고 shorts·cardnews만".

### 로컬 PC 업데이트를 부사수 PC에 적용 (브랜치 `main`, 원격 origin)
- **자동(권장,1회)**: 부사수 PC `CODEX_VIDEO_DESK\수신PC_자동업데이트_켜기.bat` → 이후 패널 켤 때마다 `git pull --ff-only` 자동.
- **수동**: `cd C:\PhoneSpot\phonespot_cardnews` → `git pull --ff-only`.
- **막히면(드리프트)**: `git fetch origin && git reset --hard origin/main` (gitignore 자산은 안 건드림).
- 코드·.bat·.mjs는 pull 즉시 반영. 의존성(pip/npm/임베딩) 변경 시에만 `SETUP_FULL_PRODUCER.bat`/패널 "시스템 업데이트" 재실행.

### 광고운영 트랙 자동 배포 (Phase 1 셋업 완료, 2026-06-11)
- 로컬 PC `apps_script/` 수정 → git push → GitHub Actions workflow가 `clasp push --force` → Apps Script 콘솔 자동 반영.
- 부사수 PC 거치지 않음 (광고운영은 Google 클라우드 + 시트만 사용).
- 콘솔에서 직접 함수 수정 = 다음 push 때 `--force`로 덮어쓰임. **콘솔 수정 ❌, 로컬 PC에서만 수정.**

---

## STEP 1 — 작업 시작 전 가이드 일괄 Read (필수)

> **★ 코드/기능 수정·디버깅이면 먼저 `_docs/SYSTEM_MAP.md`(클로드용 개발 맵)부터.**
> 기능이 대단원(A 패널 / B 카드뉴스 / C 영상 / D 라이브러리·멀티PC / E 의미매칭·임베딩 /
> F Git·멀티PC·리포위생 / G 광고 / H 자동화 / I 인코딩규칙 / J 기사스펙)으로 갈려 있고,
> 각 단원에 경로·핵심 함수·"수정 시 읽을 것"·함정이 박혀 있음. **해당 단원만 읽고 고치면 됨**(전체 X).
> 콘텐츠 작업(수집·발행·캡션)은 아래 마스터 가이드대로 진행.

**공통 (항상 Read):**

0. `_docs/TOPIC_ENGINE.md` — ★ **주제 생성기 정본 (2026-06-23 격상)**. 클로드 역할 = 주제 생성, 구현(카드·영상·실사)은 별개 트랙. 소스 5갈래·떡상점수·라인→트랙 매핑. "주제 생성/수집" 시 최우선 Read
1. `_docs/INSTRUCTIONS_CARDNEWS.md` — 시스템·자동화·후보 수집·발행 룰 마스터
2. `cardnews/templates/caption_template.md` — 5채널 + 나레이션 카피·캡션·후킹 룰
3. `_docs/CARDNEWS_BUILD.md` — 카드뉴스 1건 빌드 전체 워크플로 (수집→발행)
4. `_docs/AUTOMATION_OVERVIEW.md` — webui·telegram listener·outbox·run_pngs 매커니즘
5. `_docs/INSTRUCTIONS_SHORTS.md` — 영상(shorts) 빌드 매뉴얼
6. `cardnews/_state/content_guide.md` — 매 사이클 학습되는 시즌·트렌드 메모 (존재 시)

**인사이트 시트 (★ 매 수집·캡션 사이클 시작 시 무조건 Read, sync_sources 자동 전달):**

7. **관리대장 시트 `유튜브_인사이트`** — Apps Script 03:40 자동 갱신 (Top 키워드·후킹 패턴·우수 영상). 매 수집 시 가중치 적용. 캡션 첫 줄 후킹 패턴 적용.
8. **관리대장 시트 `메타_인사이트`** ★ 시트 추가 필요 (현재 Drive MD) — Top 헤드라인 패턴·우수 광고. 매 캡션 작성 시 짧은 채널 후킹 적용.

→ 시트 sync 안 되면 "인사이트 0건, 가중치 미적용" 1줄 명시 후 진행. 매커니즘·포맷·자가 검증 = `_docs/INSIGHTS_LOOP.md`.

**조건부 (작업 유형 따라 추가 Read):**

- 실사 AI 광고 영상 (Higgsfield, Claude 담당): `shorts/promo_ai/README.md` + `shorts/promo_ai/WORKFLOW.md`
- 타이포 광고 영상 (Remotion, 수동/코덱스): `shorts/promo/README.md` + `shorts/promo/GUIDE_TYPOGRAPHY.md`
- 카드뉴스 → 캐주얼 숏폼 (코덱스 담당): `CODEX_VIDEO_DESK/README.txt`
- **카드뉴스 기사 작성 (Claude 담당, 주제선정→영상/카드뉴스 분기)**: `cardnews/templates/article_authoring_spec.md`
- **멀티PC 독립생산 + 일러스트 Drive 공유**: `CODEX_VIDEO_DESK/MAINTENANCE/MULTI_PC_STANDALONE_AND_LIBRARY_SHARING_GUIDE.md`
- **최근(2026-06) 변경 종합**: `CODEX_VIDEO_DESK/MAINTENANCE/PHONESPOT_UPDATES_2026-06_GUIDE.md`
- **노트북 개발 / 사무실 실행 / GitHub 연동**: `_docs/DEV_LAPTOP_OFFICE_RUN_GITHUB.md`
- **패널/페이지 디자인 (색·토큰·컴포넌트 재사용)**: `_docs/DESIGN_SYSTEM.md` (server.py `:root` 정본 추출 — 패널·광고 생성기·브랜드 페이지 공용 디자인 언어)
- **광고 운영 자동화 (메타·인스타·네이버·인사이트)**: `ads/SNS_AUTOMATION_ROADMAP.md`(채널별 가능여부 매트릭스) + 작업 채널 가이드 (`ads/META_AUTOMATION.md` / `ads/NAVER_AUTOMATION.md` / `ads/INSTAGRAM_AUTOMATION_PENDING.md`(완료 헤더))
- **멀티 브랜드 모노레포 (KT/국민/진짜폰스팟 등 신설)**: `ads/MULTI_BRAND_ARCHITECTURE.md` — `_shared/`+`brands/<brand>/` 분리, clasp+GitHub, Phase 1~4
- **재해 복구 (PC 손상/실수 삭제/PC 교체/repo 삭제)**: `_docs/DISASTER_RECOVERY.md` — 시나리오 A/B/C, 자산별 백업 출처 매트릭스, `_secrets/` 별도 백업 절차, 검증

각 Read 결과는 다음 작업의 컨텍스트로 직접 활용. 사장님이 "수집해줘" / "발행해줘" / "매커니즘 알려줘" 같은 짧은 명령만 줘도 위 가이드로 모든 형식·룰을 자동 적용해야 함.

---

## STEP 2 — 작업 유형별 진입점

| 사장님 명령 패턴 | 첫 행동 |
|---|---|
| **"수정" / "고쳐줘" / "디버깅" / "기능 추가" / "왜 안돼" / 코드 작업** | `_docs/SYSTEM_MAP.md` 0번 인덱스에서 대단원(A~J) 찾기 → 그 단원 "수정 시 읽을 것"만 Read → 수정 → "함정" 체크 → 검증. 전체 파일 통독 ❌ |
| **"주제 생성" / "주제 뽑아" / "신규 수집" / "news 수집" / "신규 카드뉴스"** | ★ **`_docs/TOPIC_ENGINE.md` 최우선 Read (주제 생성기 정본, 2026-06-23 격상).** 클로드=주제 생성만(구현 분리). 소스 5갈래(①뉴스 RSS+검색 ②성과 시트 ③트렌드밈 ④시즌 ⑤carryover) 자동 합침 → (1) 시트 `유튜브_인사이트`+`인스타` Read (2) `cardnews/articles/*.json` Glob dup 회피 (3) 검증완료 주제만 (4) **주제 풀 표 = 라인·추천트랙(카드/카드영상/실사viral)·포맷·한줄요약·떡상점수**. 사장님은 번호+트랙 지정 → 해당 구현 분배 |
| "N번 발행" / "N+M 발행" / 숫자 회신 | `CARDNEWS_BUILD.md` 워크플로 따라 JSON + prompt.md + outbox 신호 |
| "프롬프트 다듬어줘" / "청크 다듬어줘" | `INSTRUCTIONS_CARDNEWS.md` 자막 청크 룰 + 매장 정합 |
| "텔레그램으로 쏴줘" | `AUTOMATION_OVERVIEW.md` outbox watcher 룰 → `_state/outbox/<날짜>_<주제>.txt` 떨굼 |
| "렌더 돌려줘" / "run_pngs" | `AUTOMATION_OVERVIEW.md` run_pngs 흐름 + 슬러그 NNN 셀렉트 |
| "영상 만들어줘" | `INSTRUCTIONS_SHORTS.md` Read 후 shorts 측 빌드 |
| "홍보영상" / "promo" / "타이포 영상" / "광고소재" | `shorts/promo/README.md` Read 후 promo 트랙 빌드 (`run_promo.bat`). 카드뉴스 영상과 다른 결(타이포/모션그래픽, 나레이션 없음·효과음+음악) |
| "슈퍼톤" / "TTS 엔진" / "나레이션 목소리" / "슈퍼톤 켜기" | `shorts/promo_ai/SUPERTONE_NARRATION.md` §8. casual 나레이션=슈퍼톤(Sora)+edge 폴백(`generate_tts.py`). 키=`_secrets/supertone_key.txt` 또는 `SUPERTONE_API_KEY`. 토글 `PHONESPOT_TTS_ENGINE`(auto/edge/supertone). 실사AI=Selena. 슈퍼톤 시 자막 근사싱크 |
| "실사 광고" / "AI 광고" / "Higgsfield" / "promo_ai" / "광교점 실사" | `shorts/promo_ai/README.md` + `WORKFLOW.md` Read → Higgsfield MCP (Kling 3.0 우선) 호출 → ffmpeg 합치기. **결제 상태 + balance 점검 필수**. 15초 9:16 광고 |
| "매커니즘 알려줘" / "이게 어떻게 돌아가" | `AUTOMATION_OVERVIEW.md` 직참조 |
| "브리핑" / "아침 브리핑" / 브리핑 포맷·시간·수신자 변경 | Claude 스케줄 task `phonespot-morning-briefing`(매일 08:00) 수정. 매커니즘·수신자 추가·진단 함정 = `_docs/SYSTEM_MAP.md` H단원 2026-07-03 항목. 수동 1회 발송 = outbox 떨굼(전원 수신) 또는 venv `tg_send.send_text(text, chat_id=...)`(개인) |
| "관리대장" / "광고운영" / "광고 시트" / "KPI" | `ads/README_FOR_AI.md` → `ads/MANUAL.md` |
| "메타 자동화" / "캠페인별 통합" / "UTM 매핑" / "GA4 매핑" | `ads/META_AUTOMATION.md` |
| "유튜브 학습" / "인사이트" / **스크립트·카피 작성 시** | `ads/YOUTUBE_LEARNING.md` + Drive `phonespot_cardnews_state/youtube_insights.md` Read → 키워드/후킹 자동 반영 |
| "메타 학습" / "광고 카피" / "광고 인사이트" / **카피·후킹 작성 시** | `ads/META_LEARNING.md` + Drive `phonespot_cardnews_state/meta_insights.md` Read → Top 키워드·헤드라인 패턴·카톡전환 우수 캠페인 자동 반영 |
| **"광고 생성기" / "카피 생성기" / "변주" / "후킹 구조" / "신규 컨셉" / "이미지 프롬프트" / generator.html·meta-sync 생성기 함수 작업** | `ads/IMPLEMENTATION_GUIDE_2026-06-09.md` (생성기 단일 정본: §0 상단 "최신 아키텍처" 먼저 → §5 함수인덱스 · §6 프롬프트). 변경 상세 = `CLAUDE.md` STEP 8 "2026-06-12 (세션 2)" |
| "KT다이렉트샵" / "KT 관리대장" | `ads_kt/README_FOR_AI.md` |
| "전체 새로고침" / "통합대시보드 갱신" / "매트릭스 갱신" / "KPI 갱신" | `Code.gs` `refreshAll()` 호출. GA4+메타+유튜브 sync → 인사이트 MD → 매트릭스/KPI/추세 차트(메타_통합 H·네이버_통합 H 자동 합산). 시트 매핑 정본 = SYSTEM_MAP G 단원 "2026-06-11 세션" |
| "네이버 동기화" / "네이버 광고그룹" / "네이버 UTM 매핑" | `ads/NAVER_AUTOMATION.md`. `syncNaverIntegrated` 매일 02:15. HMAC-SHA256 + `/stats` 호출 시 `statType` 빼기 + `ids`는 콤마 구분(JSON 배열 X). KT 자동 제외 필터 |
| "당근 자동화" / "당근 통합" / "당근 GA4 매칭" / "당근_통합 시트" | `ads/DANGGN_AUTOMATION.md`. API 없음 = 수기 입력 + `syncDanggnGA4` 매일 02:30 GA4 매칭만. 17컬럼 단순화 (메타_통합 19컬럼에서 ID 2개 제외). `DANGGN_UTM_SOURCE` Script Property 등록 필수(GA4 실제 sessionSource 값). 시트 메뉴 🥕 당근 자동화 |
| "시트 read" / "시트 구조 확인" / "시트 스냅샷" / "Drive snapshot" | B1 셋업: `apps_script_sheet_export/` 별도 프로젝트 (web app) + Drive 폴더 `PhoneSpot Sheet Snapshots`(매일 03:00 30탭 JSON 자동 저장 + `__headers.json` 전체 탭 헤더). 클로드 = Drive MCP `read_file_content`로 read. 정본 = `ads/MULTI_BRAND_ARCHITECTURE.md` 또는 CLAUDE.md STEP 8 2026-06-15 세션 3 |
| **"GA4" / "GA4 수집" / "GA4 연결" / "citymarket_arrival" / "가격확인율" / "UTM 슬러그 매핑" / "페이지별 퍼널" / "리틀리 시티마켓 분리" / GA4 탭·수집·소비 수식 작업** | **★ 별도 GA4 전담 task로 진행 (2026-07-16 종민 결정).** 인수인계 정본 = `_docs/GA4_TASK_시작프롬프트.md` (연결방식·현행구조·탭구조·트리거·검증법·함정·우선과제 P1~P4). 새 세션 시작 명령: `_docs/GA4_TASK_시작프롬프트.md 읽고 GA4 task 시작. 먼저 현황 진단부터.` 소유영역=GA4 코드만(타 task 파일 ❌). **★ 페이지별 퍼널(리틀리/시티마켓 분리, P4)** = `apps_script/page-funnel.js` + 탭 `페이지별_퍼널`·`GA4_페이지별`, `_설정` 키 `PF_A/B_PATHS`·`PF_NOTSET_BUCKET`로 조정 — 상세 = `_docs/SYSTEM_MAP.md` G단원 "2026-07-21 세션" |
| "인스타 동기화" | `ads/INSTAGRAM_AUTOMATION_PENDING.md`(완료 헤더). `syncInstagramDaily` 매일 02:00. INSTAGRAM_BUSINESS_ID 등록 + 토큰 신규 발급(scopes는 발급 시점 확정) |
| "SNS 자동화" / "스레드 자동화" / "카카오 채널 자동화" / "틱톡 자동화" / "네이버 블로그 자동화" | `ads/SNS_AUTOMATION_ROADMAP.md` 매트릭스 확인. 카카오 채널·당근·네이버 블로그 = API 없음 확정 |
| "멀티 브랜드" / "KT 시트" / "국민인터넷 시트" / "진짜 폰스팟" / "브랜드 분리" / "공용 코드 배포" / "clasp" / "push-all" | **★ 별도 task로 진행 (2026-06-15 사장님 결정).** 광고운영 task가 안 만짐. 정본 = `ads/MULTI_BRAND_ARCHITECTURE.md` "다른 task 충돌 방지 — 책임 분담" 섹션. 별도 클로드 세션 시작 명령: `ads/MULTI_BRAND_ARCHITECTURE.md 읽고 Phase 2 진행. _shared/ 폴더 분리 + brands/phonespot/ 셋업` |
| "카드뉴스 기사 써줘" / "주제 뽑아줘" / "기사 만들어줘" | `cardnews/templates/article_authoring_spec.md` → 주제제안(content_guide)→사실수집→기사 JSON 저장. 영상만이면 카드이미지·image_prompts 생략 |
| "부사수 셋업" / "새 PC" / "멀티PC" / "독립 셋업" | `부사수PC_원클릭_셋업.bat`(빈 PC 한 파일) + MULTI_PC 가이드 |
| "일러스트 공유" / "라이브러리 동기화" / "허브" | 패널 "관리>라이브러리 동기화" 또는 `라이브러리_공유_동기화.bat`. 허브=Drive `PhoneSpot_Library`(데스크톱 동기), 경로파일 `shorts/config/library_share_path.txt` |
| "주제(기사) 깃에 올려" / "전파" | `기사_깃에_올리기.bat`(대표 push) → 부사수 git pull |
| "노트북 개발" / "깃허브 연동" / "사무실에서 실행" / "이어받기" | `_docs/DEV_LAPTOP_OFFICE_RUN_GITHUB.md` — 노트북=개발(push), 사무실=실행(pull). clone/pull/push 명령 포함 |
| **"시세 사이트" / "citymarket" / "/pb" / "공개사이트" / "성지 사이트" / "셀프가입 페이지" UI/UX** | `_docs/SYSTEM_MAP.md` **K단원** Read → 시안 `citymarket_pb/index.html` 수정. 정본=라이브 `citymarket.co.kr/pb`(백엔드 다중파일, 상세=`/applyInquiry`). 실서비스 반영은 홈+applyInquiry 매핑 별도 |

---

## STEP 3 — 사장님 사용 패턴 메모리

- **사장님(종민) 선호**: 모르는 거 아는 척 ❌, 듣고 싶어 할 얘기 ❌, **팩트만 + 수학적·논리적**.
- 응답 톤 짧게. 미사여구·과한 보고 ❌. "방금 한 일" 요약 ❌.
- 매뉴얼 인용 시 줄 번호로 직접 가리키기 (예: `INSTRUCTIONS_CARDNEWS.md:329-352`).
- 옵션 제시는 정직한 한계 동봉. **클로드가 권장 강요 ❌**. 사장님이 직접 선택.
- **★ 모든 task(광고운영·카드뉴스·영상·기사 등) 코드/파일 변경을 끝낼 때마다 cmd 푸시 코드를 항상 같이 줄 것** (종민 요청 2026-06-18 광고운영 → 2026-06-19 전체 task로 확대). "bat 돌려라"로 대체 ❌ — 실제 명령을 매번 명시. git이 PATH에 없으니 형식: (stale lock 걸리면 먼저 `del /f /q C:\backup\phonespot_cardnews\.git\index.lock 2>nul`) `cd /d C:\backup\phonespot_cardnews` → `set GIT="C:\Program Files\Git\cmd\git.exe"` → `%GIT% add -A`(특정 영역만 올릴 땐 폴더 지정; 광고=apps_script) → `%GIT% commit -m "..."`(ASCII 메시지, cmd 인코딩 안전) → `%GIT% push origin main`. safe.directory·user.identity는 이미 설정됨. 영상/카드뉴스 track은 패널 '시스템 업로드'(commit 게이트 포함)도 가능하나 **cmd도 항상 함께** 제공. (보조 bat: `광고_깃에_올리기.bat`·`기사_깃에_올리기.bat`.)
- **★ 멀티브랜드 상시 적용 (종민 2026-07-13)**: 모든 코드/대시보드/시트 변경은 **폰스팟 + KT폰샵 둘 다 무조건 100% 상시 적용**. "어느 브랜드에 적용?"을 **묻지 말 것**. 코드는 push→GitHub Actions clasp가 양쪽 scriptId 자동 배포(멀티브랜드 허브). 가이드/문서도 브랜드 구분 없이 "둘 다" 전제로 기술. 사장님은 각 시트에서 재빌드/메뉴 실행만 양쪽에.

---

## STEP 4 — 시스템 진입점 파일 (작업 시작용)

| 항목 | 경로 | 용도 |
|---|---|---|
| **패널 기동(무창)** | `CODEX_VIDEO_DESK/dashboard/panel_hidden.vbs` (고정=`작업표시줄에_패널_고정.bat`) | wscript→bat 히든→`pythonw` 서버. 작업표시줄 콘솔 없이 백그라운드 상주. 직접실행/디버그=`00_PHONE_SPOT_PANEL.bat`. pin_panel.ps1 변경 시 고정 bat 1회 재실행 |
| webui | `cardnews/webui/app.py` (`webui/start.bat`) | Flask 컨트롤 패널 |
| 셀렉트 렌더 | `cardnews/run_pngs.bat` | 슬러그 셀렉트 + 18 JPG 생성 |
| 텔레그램 listener | `automation/scripts/telegram_listener.py` | 폰 → PC 명령 + outbox 푸시 |
| 텔레그램 송신 헬퍼 | `automation/scripts/tg_send.py` | 1회 송신 CLI |
| 영상 빌드 | `shorts/` 디렉터리 + Remotion | 카드뉴스 기반 영상(casual/newsroom) |
| **홍보영상(promo)** | `shorts/promo/README.md` → `run_promo.bat` | 타이포/모션그래픽 홍보 쇼츠 (Remotion 기생, 나레이션 없음·효과음+음악·스타일별 SFX·무드 음악풀) |
| **실사 AI 광고(promo_ai)** | `shorts/promo_ai/README.md` + `WORKFLOW.md` | 15초 9:16 실사 광고. Higgsfield MCP (Kling 3.0 1순위 / Seedance 2순위) → ffmpeg 합치기. Claude 담당 |
| 코덱스 영상 데스크 | `CODEX_VIDEO_DESK/` | 별도 task |
| **광고운영 관리대장** | `ads/README_FOR_AI.md` → `ads/MANUAL.md` | 폰스팟 시트·KPI·메타·GA4 자동화 |
| **메타 API 자동화** | `ads/code/apps_script/meta-sync.gs` + `ads/META_AUTOMATION.md` | 메타 광고 + GA4 통합 + 인스타(syncInstagramDaily 매일 02:00) |
| **네이버 검색광고 자동화** | `ads/code/apps_script/naver-sync.gs` + `ads/NAVER_AUTOMATION.md` | 광고그룹 단위, HMAC-SHA256, KT 자동 제외, 매일 02:15 |
| **SNS 자동화 가능성 매트릭스** | `ads/SNS_AUTOMATION_ROADMAP.md` | 콘텐츠/광고 채널별 가능여부 + 권장 순서 |
| **멀티 브랜드 아키텍처 (제안)** | `ads/MULTI_BRAND_ARCHITECTURE.md` | `_shared/`(공용 코드) + `brands/<brand>/`(데이터·설정) + clasp+GitHub. Phase 1~4. KT/국민/진짜폰스팟 확장 대비 |
| **KT다이렉트샵 관리대장** | `ads_kt/README_FOR_AI.md` | KT 별도 시트 |
| **부사수 PC 원클릭 셋업** | `CODEX_VIDEO_DESK/부사수PC_원클릭_셋업.bat` | 빈 PC 1파일: git/node/python+clone+풀셋업 |
| **풀 생산기 셋업(클론 후)** | `CODEX_VIDEO_DESK/SETUP_FULL_PRODUCER.bat` | 카드뉴스+영상 의존성+임베딩+검증 |
| **환경 점검** | 패널 "관리>환경 점검" / `shorts/scripts/codex_producer_check.py` | 자원 PASS/FAIL |
| **기사 작성 스펙** | `cardnews/templates/article_authoring_spec.md` | Claude 기사 JSON 작성 기준 |
| **기사 git 전파** | `CODEX_VIDEO_DESK/기사_깃에_올리기.bat` | articles+.gitignore commit&push (articles는 git 추적=중복방지 DB) |
| **일러스트 공유 동기화** | 패널 "관리>라이브러리 동기화" / `CODEX_VIDEO_DESK/라이브러리_공유_동기화.bat` | Drive 허브 양방향 병합. 렌더 직전 자동 동기화도 됨 |
| **일러스트 허브 경로설정** | `CODEX_VIDEO_DESK/일러스트_공유허브_경로설정.bat` | PC별 1회, Drive 로컬경로 기입 |
| **라이브러리 백업/스케줄** | `라이브러리_백업.bat` / `라이브러리_자동백업_스케줄_등록.bat` | 스냅샷(회전10) / 매일 09:00 |
| **수신 PC 자동 코드 업데이트** | `CODEX_VIDEO_DESK/수신PC_자동업데이트_켜기.bat` | 마커 ON → 패널 시작 시 git pull(부사수만) |

---

## STEP 5 — 폴더 구조 (높은 수준)

```
phonespot_cardnews/
├── CLAUDE.md                     ← 이 파일 (부트스트랩)
├── _docs/                        ← 가이드 모음 (반드시 모두 Read)
│   ├── INSTRUCTIONS_CARDNEWS.md  마스터 매뉴얼
│   ├── CARDNEWS_BUILD.md         빌드 워크플로
│   ├── AUTOMATION_OVERVIEW.md    매커니즘
│   ├── INSTRUCTIONS_SHORTS.md    영상 매뉴얼
│   ├── SETUP_GUIDE.md            초기 셋업
│   ├── SETUP_WINDOWS.md          Windows 환경
│   └── PORTABILITY.md            이식 가이드
├── _secrets/                     ← .gitignore (API 키·토큰)
├── _state/                       ← 런타임 상태
│   ├── outbox/                   클로드가 떨궈둔 텔레그램 송신 큐
│   └── outbox_sent/              송신 완료 보관
├── cardnews/
│   ├── articles/                 NNN_<type>_<topic>.json
│   ├── images/                   NNN_<type>_<topic>/prompt.md + 1~5.png
│   ├── output/                   18 JPG + captions.md (렌더 결과)
│   ├── templates/                
│   │   └── caption_template.md   카피·캡션 룰
│   ├── webui/                    Flask 패널
│   ├── scripts/                  렌더·도구
│   └── _state/                   카드뉴스 사이클 메모
├── shorts/                       영상 (Remotion: casual/newsroom 카드뉴스영상)
│   ├── promo/                    ★ 타이포/모션그래픽 홍보영상 (진입점 README.md, run_promo.bat)
│   └── promo_ai/                 ★ 실사 AI 광고영상 (진입점 README.md + WORKFLOW.md, Higgsfield Kling 3.0/Seedance, ffmpeg 합치기, Claude 담당)
├── automation/                   listener·자동화 스크립트
├── CODEX_VIDEO_DESK/             코덱스 영상 task (별도)
├── ads/                          ★ 광고운영 관리대장 (폰스팟)
│   ├── README_FOR_AI.md          AI 진입점 — Sheet ID + 자동화 흐름
│   ├── MANUAL.md                 매일/주간/월간 운영 매뉴얼
│   ├── META_AUTOMATION.md        메타 API + GA4 + UTM 매핑 통합 가이드
│   ├── code/apps_script/
│   │   ├── Code.gs               시트 자동화 (KPI/매트릭스/SNS)
│   │   └── meta-sync.gs          메타 API 자동 동기화 (campaign/소재/UTM)
│   └── data/
│       ├── sheet_structure.md    시트 컬럼 구조
│       └── utm_mapping_design.md UTM_매핑 시트 설계
├── ads_kt/                       ★ KT다이렉트샵 관리대장 (별도 시트)
└── upload/                       SNS 업로드 자료
```

---

## STEP 6 — 다른 세션과의 연동 (★ 하네스)

본 CLAUDE.md 가 모든 가이드의 단일 진입점. 다른 클로드 코드 세션·코덱스 등이 이 폴더에서 작업할 때:

1. **자동 Read** — Claude Code CLI 는 cwd 의 `CLAUDE.md` 를 자동 Read. Cowork mode 는 폴더 마운트 시 진입 메시지에 본 파일 포함되도록 사용자 설정 권장.
2. **가이드 업그레이드 시** — 매뉴얼·캡션템플릿·빌드가이드 어느 하나 변경됐다면 본 CLAUDE.md 의 STEP 1 리스트 갱신·버전 메모 추가
3. **다른 task와 매커니즘 공유** — 영상 task (CODEX_VIDEO_DESK) 도 자체 README 외에 본 CLAUDE.md 참조. 카드뉴스 측 자동화 (outbox·webui) 변경 시 영상 측에 영향 점검
4. **결과 저장 규약** — 모든 task 산출물은 표준 폴더 (articles/·images/·output/·shorts/) 에만 저장. 임의 위치 ❌
5. **명령 없이 자동 실행** — 사장님 짧은 명령 ("수집"·"발행"·"렌더") 으로 위 STEP 2 매트릭스 따라 즉시 동작. 가이드 추가 질문 ❌

---

## STEP 7 — 리포 위생: 중복 실행파일·줄끝 오염 방지 (★ 2026-06-08)

### 왜 생겼나
1. **모노레포가 겹치는 하위트리를 import로 합침** — 루트와 `CODEX_VIDEO_DESK/`가 각자 setup/sync 스크립트를 들고 들어와 사본 누적(canonical 위치 규칙 부재).
2. **MAINTENANCE의 MIGRATE/INSTALL/APPLY `.py`가 `.bat/.ps1`을 문자열 템플릿 생성·`shutil.copy2`로 복사** → byte 동일 사본 + 템플릿 복붙 본문 미수정 → "이름 다른데 내용 같은" 버그.
3. **`.gitattributes` 부재** → CRLF/LF/BOM 혼재 → 유령 diff·편집 truncation.
4. **다중 writer**(노트북 + 실행 PC 둘 다 push) → 같은 파일 병렬 수정 → diverge/충돌. STEP 0의 "push는 노트북만"으로 차단.

### 규칙
1. 실행파일 **단일 위치(SSOT)** — 루트 편의 복사 금지, 필요하면 사본 말고 얇은 래퍼.
2. 새/수정 `.bat`·`.ps1` 커밋 전 **중복 md5 점검**(아래). 동일 발견 시 통합.
3. 템플릿 복붙 시 **본문 대상명까지 교체**.
4. `.gitattributes`로 줄끝 고정 + 한글 bat BOM 유지.
5. `.bat/.ps1` 편집은 **HEAD 재구성+치환**(Edit툴 truncation 회피), 편집 후 `file`로 BOM·줄끝 검증.

### 중복 점검 스니펫
```
git ls-files -z | grep -ziE '\.(bat|ps1|cmd|vbs)$' | xargs -0 md5sum | sort \
 | awk '{h=$1;$1="";a[h]=a[h]"\n  "$0;c[h]++} END{for(h in a) if(c[h]>1) print c[h]" identical:"a[h]"\n"}'
```
※ `CODEX_VIDEO_DESK/MAINTENANCE/`의 APPLY/RUN/ROLLBACK은 패치 적용/롤백 툴 — 중복 아님, 삭제 금지.

---

## STEP 8 — 변경 이력

> 분리됨 -> `_docs/CHANGELOG.md`. 하네스 변경 시 거기에 1줄.
