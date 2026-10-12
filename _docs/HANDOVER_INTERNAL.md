# 사내 인수인계 가이드 — 시스템 설명서 + 재가동 가이드

> 작성 2026-10-12 · 범위 = **사내 직원에게 넘김(소유권은 회사·사장님 유지)** · 대상 = 전체 시스템
> **넘기는 방식 = "휴면 인수인계"**: 받는 사람은 ① 이 문서로 무엇인지 파악 → ② 쓰고 싶은 모듈만 §3 순서대로 자기(또는 회사) 계정을 연결해 다시 켠다. 안 쓰면 아무것도 안 해도 됨.
> 상위 = `CLAUDE.md` → `_docs/SYSTEM_MAP.md` F단원. 짝 문서 = `_docs/DISASTER_RECOVERY.md`(키 재발급 절차 정본).
> 표기: [사실] 코드·공식문서 확인 · [미확인] 확인 못 함 · [결정] 사장님이 정할 것

---

## 1. 이 시스템은 무엇인가 (사람용 요약)

휴대폰 매장 **폰스팟**의 홍보 콘텐츠를 만들고 광고 성과를 모으는 사내 도구 묶음. 한 GitHub 저장소(모노레포)에 들어 있고, 모듈마다 따로 켜고 끌 수 있다.

| 모듈 | 하는 일 | 결과물 | 핵심 위치 |
|---|---|---|---|
| **M1 주제·기사** | 뉴스·트렌드에서 주제를 뽑고 기사 JSON 작성 (Claude가 수행) | `cardnews/articles/*.json` | `_docs/TOPIC_ENGINE.md`, `cardnews/templates/article_authoring_spec.md` |
| **M2 카드뉴스** | 기사 + 이미지 → 인스타용 카드 이미지 | `cardnews/output/<slug>/` JPG 18장 | `cardnews/run_pngs.bat`, `_docs/CARDNEWS_BUILD.md` |
| **M3 영상** | 기사 → 9:16 쇼츠(나레이션·자막·일러스트), 타이포 홍보영상, 커버 | `CODEX_VIDEO_DESK/RESULTS/*.mp4` | `shorts/run_codex_casual.bat`·`run_promo.bat`·`run_cover.bat`, `_docs/INSTRUCTIONS_SHORTS.md` |
| **M4 제작 패널** | 브라우저 화면에서 M2·M3를 버튼으로 실행·기록 확인. 다른 PC를 렌더 워커로 붙일 수 있음 | (화면) | `CODEX_VIDEO_DESK/dashboard/`, `CODEX_VIDEO_DESK/PANEL_TASK.md` |
| **M5 광고 관리대장** | 구글 시트 + Apps Script로 메타·네이버·GA4·유튜브·인스타 성과 자동 수집, KPI·인사이트, 광고 카피 생성기 (폰스팟·KT폰샵 2개 시트) | 구글 시트 | `apps_script/`, `ads/README_FOR_AI.md`, `ads/MANUAL.md` |
| **M6 알림·브리핑** | 텔레그램 봇으로 작업 알림·폰 명령·매일 08:00 아침 브리핑 | 텔레그램 메시지 | `automation/scripts/telegram_listener.py`, H단원 |
| **M7 실사 AI 광고** | Higgsfield로 15초 실사 광고 생성 (Claude가 수행) | mp4 | `shorts/promo_ai/README.md` |
| **M8 유튜브 학습** | 유튜브 채널 성과를 받아 시트에 기록·패턴 분석 | 시트 탭 | `ads/integrations/youtube/` |

- **흐름**: M1 기사 → M2 카드뉴스 / M3 영상 (M4 패널로 조작) → 업로드·광고 집행 → M5가 성과 수집 → 다음 주제에 반영(M1).
- **Claude의 역할**: 이 폴더의 `CLAUDE.md`가 Claude용 작업 규칙(하네스). Claude를 이 폴더에 연결하면 같은 규칙으로 주제 생성·기사 작성·코드 수정을 이어받는다.
- **PC 역할** (`CLAUDE.md` STEP 0): 로컬 PC = 수정·push / 부사수 PC = 렌더 전용(pull only).

---

## 2. 개인 계정에 연결된 지점 (★ 질문 답)

**[사실] 있다.** 현재 거의 전부 사장님 개인 계정(313jongmin)에 묶여 있다. 받는 사람이 그 모듈을 켜려면 아래 지점마다 **회사 계정 또는 본인 계정을 다시 연결**해야 한다.

| # | 연결 지점 | 지금 묶인 계정 | 어디에 박혀 있나 | 이게 없으면 | 모듈 |
|---|---|---|---|---|---|
| A1 | **GitHub 저장소** | 사장님 개인 GitHub `313jongmin-droid` | 저장소 소유 + Actions Secrets 8개 | 코드 받기·업데이트 불가(zip 복사로는 실행 가능) | 전체 |
| A2 | **Google 계정 (시트·Apps Script·Drive)** | 사장님 개인 Gmail | 관리대장 시트 2개·Apps Script 프로젝트 3개(폰스팟·KT·sheet_export)·Drive `PhoneSpot_Library` | M5 전체, 일러스트 공유 | M5, M3 |
| A3 | **Apps Script 자동 실행(트리거 21종)** | 만든 사람 = 사장님 [사실: 설치형 트리거는 만든 사람 권한으로 실행] | Apps Script 프로젝트 | 매일 자동 수집 정지 | M5 |
| A4 | **Apps Script 자동 배포 토큰** | 사장님 Google 로그인 토큰 | GitHub Secret `CLASPRC_JSON` (`.github/workflows/deploy-apps-script.yml:56~58`) | push해도 시트 코드 반영 안 됨 | M5 |
| A5 | **웹앱 접근 허용 이메일** | `313jongmin@gmail.com`, `mazision@gmail.com` | `apps_script/Code.js:590` (사본 `ads/code/apps_script/Code.gs:64`) | 다른 계정은 생성기 웹앱 "접근 권한 없음" | M5 |
| A6 | **광고 API 키** (META_TOKEN·NAVER 3종·GOOGLE_ADS 6종·APIFY·GEMINI·TELEGRAM) | 각 서비스의 사장님/회사 계정 | Apps Script 스크립트 속성 | 해당 채널 수집 정지 | M5 |
| A7 | **Google Cloud 서비스 계정** | GCP 프로젝트 `phonespot-sns-analytics` | `_secrets/sheets_service_account.json` (로컬, git 미포함) | 유튜브 학습 결과 시트 기록 불가 | M8 |
| A8 | **유튜브 분석 OAuth 토큰** | 유튜브 채널 소유 Google 계정 | `upload/tokens/yt_client_secret.json`·`yt_analytics_token.json` (로컬, git 미포함) | 유튜브 성과 수집 불가 | M8 |
| A9 | **텔레그램 봇** | 봇 만든 사람(사장님) + chat_id | `_secrets/telegram_token.txt`·`telegram_chat_id.txt`·`listener_config.json`(`trusted_chat_ids`·`broadcast_chat_ids`), GitHub Secrets | 알림·폰 명령·브리핑 없음 | M6 |
| A10 | **Claude 계정** | 사장님 Claude | 스케줄 task `phonespot-morning-briefing`, 사용자 메모리 | 주제·기사 작성, 아침 브리핑 | M1, M6, M7 |
| A11 | **Supertone** | 사장님 키 | `_secrets/supertone_key.txt` | **없어도 동작** — 무료 edge-tts로 자동 대체(`shorts/scripts/generate_tts.py:38~52`) | M3 |
| A12 | **Gemini 키** (로컬) | 사장님 키 | `_secrets/gemini_key.txt` | **없어도 대부분 동작** — 사진 태깅 스킵(`codex_photo_tag.py`), 타이포 카피는 템플릿 대체(`promo_generate.py`). 단 `cardnews/scripts/generate_image.py`(Gemini 이미지 생성)는 키 필요 | M2, M3 |
| A13 | **ChatGPT** (이미지 생성) | 사용하는 사람 본인 로그인 | 브라우저 세션 (`automation/scripts/chrome_chatgpt.py`) | 카드·영상용 이미지를 다른 방법으로 만들어야 함 | M2, M3 |
| A14 | **Higgsfield** | 사장님 계정 + 결제 | Claude 커넥터 | 실사 광고 불가 | M7 |
| A15 | **Meta 비즈니스·네이버 검색광고·GA4·Google Ads** | 사장님/회사 비즈니스 계정 | 각 서비스 콘솔 | 광고 집행·데이터 원천 | M5 |
| A16 | webui 비밀번호 | — | `_secrets/webui_auth.txt` | 카드뉴스 webui 로그인 | M2(webui) |
| A17 | citymarket.co.kr 라이브 사이트 | [미확인: 호스팅·관리 주체] | 리포 밖 | — | K단원 |

**핵심 정리**:
- **개인 계정 없이 바로 돌아가는 것** = M2 카드뉴스 렌더(이미지가 이미 있으면), M3 영상 렌더(edge-tts·키 없음 대체), M4 패널. 필요한 건 코드(GitHub 접근 또는 폴더 복사) + 셋업뿐.
- **계정 연결 없이는 안 도는 것** = M5 광고 관리대장 전체, M6 텔레그램, M8 유튜브 학습, M1·M7(Claude·Higgsfield).
- 가장 큰 의존 = **A2~A4 (사장님 Google 계정)**. 사장님 계정에 문제가 생기면 M5 전체가 멈춘다 → §5 D6.

---

## 3. 재가동 가이드 (필요한 모듈만, 위에서부터)

### 3.0 공통 (모든 모듈의 전제)
1. 사장님이 GitHub 저장소에 받는 사람을 Collaborator로 초대(읽기 권한이면 충분 — §5 D3) → 수락.
2. 받는 사람 PC(Windows)에서 `CODEX_VIDEO_DESK/부사수PC_원클릭_셋업.bat` 실행: Git·Node·Python 설치 → 저장소 clone → `SETUP_FULL_PRODUCER.bat`(npm·pip·크롬·임베딩 ~1GB) → Google Drive 설치(선택).
3. 패널 실행(`CODEX_VIDEO_DESK/00_PHONE_SPOT_PANEL.bat`) → 관리 > **환경 점검** 전부 PASS 확인.
4. 이 PC는 pull only: `CODEX_VIDEO_DESK/수신PC_자동업데이트_켜기.bat`. 패널 "GitHub 업로드" 사용 금지(STEP 0-2).

### 3.1 M2 카드뉴스 · M3 영상 · M4 패널 — **계정 없이 가능**
1. 3.0 완료.
2. (선택) 일러스트 공유: 사장님이 Drive `PhoneSpot_Library` 공유(A2) → Drive 동기화 → `CODEX_VIDEO_DESK/일러스트_공유허브_경로설정.bat`.
3. (선택) 더 좋은 나레이션: Supertone 키를 `_secrets/supertone_key.txt`(A11). 없으면 edge-tts.
4. 확인: 패널에서 기존 슬러그 1개 → 카드 생성 / 영상 렌더 → `cardnews/output/<slug>/`, `CODEX_VIDEO_DESK/RESULTS/` 생성.

### 3.2 M1 주제·기사 (Claude)
1. 받는 사람 Claude 계정(Cowork)에서 이 저장소 폴더 선택 → `CLAUDE.md`가 자동 적용.
2. 명령 예: "주제 생성" / "N번 기사 써줘" (`CLAUDE.md` STEP 2).
3. 새 기사 공유는 git push가 필요 → **push는 로컬 PC에서만**(STEP 0). 받는 사람 PC에서 만든 기사는 로컬 PC로 옮겨 push하거나 §5 D2 결정.

### 3.3 M6 텔레그램 알림·브리핑
1. 텔레그램 BotFather에서 새 봇 생성(또는 기존 봇 토큰 인계) → `_secrets/telegram_token.txt`, 본인 chat_id → `_secrets/telegram_chat_id.txt` (A9). 절차 = `DISASTER_RECOVERY.md` "TELEGRAM_BOT_TOKEN" 항목.
2. listener 실행: `automation/scripts/telegram_listener.py`.
3. 아침 브리핑: 받는 사람 Claude 계정에서 스케줄 task를 새로 만듦(사장님 계정 task는 옮겨지지 않음). 내용 정본 = SYSTEM_MAP H단원 2026-07-03.

### 3.4 M5 광고 관리대장 (가장 무거움)
- **방식 [결정 D6]**: (a) 사장님 계정 그대로 두고 받는 사람에게 공유만 / (b) 회사 공용 Google 계정으로 시트·Apps Script 소유 이전 후 재연결.
- (a)의 경우:
  1. 시트 2개·Apps Script 3개 공유(A2). 트리거는 사장님 계정 유지(A3).
  2. 웹앱 허용 이메일에 받는 사람 추가(A5, `apps_script/Code.js:590`) → 로컬 PC에서 push → Actions가 배포.
  3. 확인: 시트 메뉴 🛠 → 🔑 토큰 연결 테스트 ✅.
- (b)의 경우(사장님 계정 의존 제거):
  1. 새 계정으로 시트·Apps Script 복사 또는 소유권 이전 [미확인: 개인 Gmail 간 소유권 이전 범위].
  2. 새 계정으로 트리거 재설치(A3), 스크립트 속성 키 재등록(A6, `DISASTER_RECOVERY.md` 재발급 절차), `clasp login` → GitHub Secrets `CLASPRC_JSON`·`CLASP_JSON(_KT/_EXPORT)` 갱신(A4), `WEBAPP_DEPLOY_ID(_KT)` 갱신.
  3. 웹앱 허용 이메일 교체(A5).
  4. 확인: 전체 새로고침(`refreshAll`) + 토큰 연결 테스트.

### 3.5 M8 유튜브 학습
1. 유튜브 채널 소유 계정으로 Google Cloud OAuth 클라이언트 → `upload/tokens/yt_client_secret.json`, 최초 실행 시 `yt_analytics_token.json` 생성(A8).
2. 시트 기록용 서비스 계정 키 `_secrets/sheets_service_account.json`(A7) + 시트에 그 서비스 계정 공유.
3. 실행: `ads/integrations/youtube/run_youtube_sync.bat`.

### 3.6 M7 실사 AI 광고
1. Higgsfield 계정·결제 + 받는 사람 Claude에 Higgsfield 커넥터 연결(A14).
2. `shorts/promo_ai/README.md` + `WORKFLOW.md` 절차.

---

## 4. 넘기기 전 사장님 체크

1. 받는 사람에게 줄 것: 저장소 접근(A1) + 이 문서 위치. **`_secrets/` 파일은 복사해 주지 않는다**(필요하면 사장님이 직접 넣거나 받는 사람이 자기 키 발급).
2. 사전 점검 결과(2026-10-12):
   - git 이력 비밀값: 468커밋·blob 2,518개(3MB 미만) 정규식 스캔 **0건**, 비밀 파일명 이력 0건 [사실]. 한계: 3MB 이상·패턴 밖 형식(네이버·Supertone 키 등) 미탐.
   - `upload/tokens/yt_*.json`은 git 미포함 확인(이력에 `.gitkeep`만).
   - 정리 후보(추적 중 잔여물): `_frames2/3/4/_tmp`(24), `local_9034ca23-…`(3), `apps_script/.fuse_hidden0000001f00000001`, `iframe_test.html`, `_sample_cover.jpg`, `_preview_*`(3), `_cover_concepts_preview.html`. 런타임 상태 파일 추적: `CODEX_VIDEO_DESK/IMPORT_PROPOSAL.json`·`CARD_IMPORT_PROPOSAL.json`·`IMPORT_CONFIRMED.used.json`(사장님 다운로드 경로 포함), `WORK_QUEUE/*`. 각 소유 task 확인 후 정리.
   - 경로 하드코딩: 코드에 `C:\backup\phonespot_cardnews`·`C:\PhoneSpot\phonespot_cardnews` 각 1곳, 문서에 메인 PC `192.168.0.7`(md 6개). 받는 사람 PC 경로가 다르면 해당 스크립트 확인.
3. **GitHub 쓰기 권한 주의**: Write 권한자는 워크플로를 고쳐 Actions Secrets(`CLASPRC_JSON` = 사장님 Google 로그인 토큰 포함)를 읽을 수 있다 [사실: GitHub 공식]. → 기본은 읽기 권한(§5 D3).
4. Apps Script 편집자는 스크립트 속성(API 키)을 볼 가능성이 높다 [미확인] → M5를 안 쓸 사람에게는 Apps Script 공유 안 함.

---

## 5. 결정 필요 (사장님)

| # | 질문 | 선택지 |
|---|---|---|
| D1 | 받는 사람 역할 | 운영자(M5 포함 전체) / 제작자(M1~M4만) / 일단 휴면(3.0만) |
| D2 | 받는 사람이 코드·기사를 push할 일이 있나 | 없음(STEP 0 유지) / 있음(PR 방식 등 — STEP 0 변경 필요) |
| D3 | GitHub 권한 | 읽기(Read) / 쓰기 + `CLASPRC_JSON`을 배포 전용 계정으로 교체 |
| D6 | Google 계정 의존 | 사장님 개인 계정 유지(공유만) / 회사 공용 계정으로 이전(§3.4 b) |

---

## 6. 권한 회수 (퇴사·역할 변경 시)

1. GitHub collaborator 제거.
2. Google 시트·Apps Script·Drive·GA4 공유 해제, Meta·네이버·Google Ads 사용자 제거.
3. `listener_config.json`에서 chat_id 제거.
4. 그 사람 PC에 있었던 키 재발급(Supertone·Gemini·서비스계정·텔레그램) — 절차 `DISASTER_RECOVERY.md`.
5. M5 운영자였다면 스크립트 속성 키·`CLASPRC_JSON` 재발급 검토.
6. 그 PC의 `_secrets/`·`upload/tokens/` 삭제 확인.

---

## 7. 출처
- 코드·스캔: 이 리포 (2026-10-12 기준), 스캔 = `git rev-list --all --objects` + `git cat-file --batch` 정규식
- [Apps Script 설치형 트리거(공식)](https://developers.google.com/apps-script/guides/triggers/installable) — 만든 사람 권한으로 실행
- [Apps Script Properties Service(공식)](https://developers.google.com/apps-script/reference/properties/) — 스크립트 속성은 그 스크립트의 모든 사용자 공유
- [GitHub Actions secrets(공식)](https://docs.github.com/en/enterprise-server@3.9/actions/security-guides/using-secrets-in-github-actions) — 파일 편집 권한이 있으면 워크플로에서 secrets 사용·읽기 가능
