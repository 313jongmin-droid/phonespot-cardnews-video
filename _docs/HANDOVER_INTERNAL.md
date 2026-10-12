# 사내 인수인계 가이드 (담당자 추가·교체·권한 회수)

> 작성 2026-10-12 · 범위 = **사내 직원에게 운영을 넘김(소유권은 회사·사장님 유지)** · 대상 = 전체 시스템(카드뉴스·영상·패널·광고운영·자동화)
> 상위 = `CLAUDE.md` → `_docs/SYSTEM_MAP.md` F단원. 짝 문서 = `_docs/DISASTER_RECOVERY.md`(키 재발급 절차 정본).
> 표기: [사실] 코드·공식문서 확인 · [미확인] 확인 못 함 · [결정] 사장님이 정할 것

---

## 0. 원칙

1. **소유는 회사(사장님) 계정, 담당자는 권한만.** 계정 자체를 넘기지 않는다(퇴사 시 회수가 쉬워야 함).
2. **비밀값은 복사해서 건네지 않는다.** 꼭 PC에 있어야 하는 키는 사장님이 직접 넣고, 담당자 퇴사 시 **그 PC에 있던 키는 재발급**(§7).
3. **역할별 최소 권한.** 아래 R1/R2 중 무엇인지 먼저 정하고 그 열만 부여.
   - **R1 운영자**: 사장님 대신 전체 운영(광고 관리대장 포함)
   - **R2 제작자**: 카드뉴스·영상 제작만
4. 머신 규칙은 `CLAUDE.md` STEP 0 그대로: **push는 로컬 PC에서만**, 그 외 PC는 pull only.

---

## 1. 사전 점검 결과 (2026-10-12 실행)

| 점검 | 방법 | 결과 |
|---|---|---|
| git 이력 비밀값 | 전체 468커밋의 고유 blob 2,518개(3MB 미만) 정규식 스캔 — 텔레그램 봇토큰·Google API키·개인키 블록·GCP 서비스계정·Meta 토큰·GitHub 토큰·sk- 키·Apify·clasp refresh_token·Slack | **0건** [사실] |
| 비밀 파일명 이력 | 이력 전체 경로에서 `_secrets/`·clasprc·credential·service_account·.env 등 | **0건** (`token` 들어간 문서·가이드 파일만 있음) [사실] |
| 스캔 한계 | 정규식 기반 | 3MB 이상 파일, 위 패턴 밖 형식(예: 네이버 키·Supertone 키)은 탐지 못 함 |
| 개인 이메일 하드코딩 | `git grep` | `apps_script/Code.js:590` 웹앱 접근 허용 목록 = `['313jongmin@gmail.com','mazision@gmail.com']` (사본 `ads/code/apps_script/Code.gs:64`) → **R1 담당자 이메일 추가 필요**(광고 task 영역 파일) |
| 텔레그램 권한 | `automation/scripts/telegram_listener.py:78~79` | `_secrets/listener_config.json`의 `trusted_chat_ids`(명령 권한)·`broadcast_chat_ids`(수신 전용)에 담당자 chat_id 추가 필요 |
| 경로 하드코딩 | `git grep` | 코드: `C:\backup\phonespot_cardnews` 1곳·`C:\PhoneSpot\phonespot_cardnews` 1곳 / 문서: 메인 PC `192.168.0.7` md 6개 파일 — 담당자 PC 경로가 다르면 해당 스크립트 확인 |
| 추적 중인 잔여물(정리 후보) | `git ls-files` | `_frames2`·`_frames3`·`_frames4`·`_frames_tmp`(24개), `local_9034ca23-…`(3), `apps_script/.fuse_hidden0000001f00000001`, `iframe_test.html`, `_sample_cover.jpg`, `_preview_*`(3), `_cover_concepts_preview.html` |
| 추적 중인 런타임 상태 | `git ls-files` | `CODEX_VIDEO_DESK/IMPORT_PROPOSAL.json`·`CARD_IMPORT_PROPOSAL.json`·`IMPORT_CONFIRMED.used.json`(사장님 다운로드 폴더 경로 포함), `WORK_QUEUE/*` — 매 작업마다 변경되는 파일이 git에 섞임 |

- 잔여물·런타임 파일 정리는 **각 소유 task 확인 후**(삭제 전 용도 확인). 인수인계 자체를 막지는 않음.

---

## 2. 계정·권한 인벤토리

| 서비스 | 용도 | 담당자에게 주는 방법 | R1 | R2 | 주의 |
|---|---|---|---|---|---|
| **GitHub** `313jongmin-droid/phonespot-cardnews-video` | 코드·기사 JSON·Apps Script 자동배포 | Collaborator 초대 | Write | Read | **Write 권한자는 워크플로를 수정해 Actions Secrets를 읽을 수 있음**[사실: GitHub 공식 "secrets를 워크플로에서 읽을 수 있다, 파일 편집 권한이 있으면"]. Secrets = `CLASPRC_JSON`(사장님 Google OAuth 토큰)·`CLASP_JSON(_KT/_EXPORT)`·`TELEGRAM_BOT_TOKEN/CHAT_ID`·`WEBAPP_DEPLOY_ID(_KT)` → §8 D3 |
| **Google 관리대장 시트** (폰스팟 URL = `ads/README_FOR_AI.md:162`, KT = `ads_kt/README_FOR_AI.md`) | 광고운영·KPI | 시트 공유 | 편집 | 보기(필요 시) | |
| **Apps Script 프로젝트** (폰스팟·KT·`apps_script_sheet_export`) | 광고 자동화(설치형 트리거 `newTrigger` 21종) | 프로젝트 공유(편집자) | 편집 | ❌ | ① **설치형 트리거는 만든 사람 계정으로 실행**[사실: Apps Script 공식] → 트리거는 사장님 계정 유지, 사장님 계정 권한 변경 시 자동화 정지 ② 스크립트 속성 19개(그중 비밀값 = META_TOKEN·NAVER 키·GOOGLE_ADS 토큰/시크릿·GEMINI·APIFY·TELEGRAM)는 프로젝트 설정에 있어 **편집자가 볼 가능성 높음**[미확인] |
| **Drive `PhoneSpot_Library`** | 일러스트 공유 허브 | 폴더 공유 + Drive 데스크톱 동기화 | 편집 | 편집 | 경로 파일 `shorts/config/library_share_path.txt`(PC별) |
| **GA4** | 유입 분석 | 속성 사용자 추가 | 뷰어/분석가 | ❌ | |
| **Meta 비즈니스** (광고계정·페이지·인스타) | 광고·인스타 동기화 | 비즈니스 포트폴리오에 사람 추가 + 자산 역할 | 필요 역할 | ❌ | 자동화는 시스템 사용자 토큰(`phonespot-sync`) — 담당자 개인 권한과 별개 |
| **네이버 검색광고** | 광고 동기화 | 계정 권한 부여 방식 [미확인] | 필요 시 | ❌ | API 키는 스크립트 속성 |
| **Google Ads** | (키 존재: `GOOGLE_ADS_*`) | 관리자 계정 사용자 추가 | 필요 시 | ❌ | |
| **텔레그램 봇** | 알림·명령·아침 브리핑 | chat_id를 `listener_config.json`에 추가 | trusted | broadcast | |
| **Supertone** | 영상 나레이션 TTS | 키 파일 `_secrets/supertone_key.txt` (사장님이 주입) | ○ | ○ | 키가 PC에 파일로 존재 → 퇴사 시 재발급 |
| **Gemini** | 인사이트 분석 | 스크립트 속성 + `_secrets/gemini_key.txt` | ○ | 필요 시 | 동일 |
| **Google 서비스 계정** `_secrets/sheets_service_account.json` | 로컬 스크립트의 시트 접근 | 사장님이 주입 | ○ | 필요 시 | 키 파일 = 계정 자격증명 |
| **Apify** | 메타 광고 라이브러리 벤치마크 | 스크립트 속성 | (속성 경유) | ❌ | |
| **업로드 채널 토큰** (Threads·TikTok·Instagram·YouTube·네이버블로그, `upload/scripts/channels/`) | SNS 업로드 | 채널별 [미확인: 현재 사용 여부] | 필요 시 | 필요 시 | |
| **ChatGPT 웹** (`automation/scripts/chrome_chatgpt.py`) | 이미지 생성 보조 | 담당자 본인 ChatGPT 로그인 | ○ | ○ | 브라우저 로그인 세션 사용 |
| **Higgsfield** (실사 AI 광고) | 실사 영상 생성 | Claude 커넥터 + 결제 계정 [미확인: 팀 공유 방식] | 필요 시 | 필요 시 | 과금 |
| **Claude** (Cowork) | 주제·기사 작성·코드 작업·아침 브리핑 | 담당자 본인 Claude 계정 + 이 폴더 마운트 | ○ | ○ | ① 이 폴더의 `CLAUDE.md` 하네스는 그대로 적용됨 ② **스케줄 task `phonespot-morning-briefing`과 사용자 메모리는 사장님 계정 소속** → 담당자 계정에서 재생성 필요 |
| **citymarket.co.kr** (K단원 라이브 사이트) | 공개 시세 사이트 | 호스팅·관리 주체 [미확인] | 필요 시 | ❌ | 리포엔 시안만 있음 |
| 당근 | 수기 입력 | 계정 공유 방식 [미확인] | 필요 시 | ❌ | API 없음 |

---

## 3. 담당자 PC 셋업 순서

1. GitHub 초대 수락 + 담당자 PC에 Git 로그인(비공개 리포 clone 권한).
2. `CODEX_VIDEO_DESK/부사수PC_원클릭_셋업.bat` 실행 — Git/Node/Python 설치 → clone → `SETUP_FULL_PRODUCER.bat`(npm·pip·크롬·임베딩 ~1GB) → Drive 설치(선택).
3. 사장님이 `_secrets/`에 역할에 필요한 키만 넣기(§2 R1/R2 열).
4. Drive `PhoneSpot_Library` 동기화 + `CODEX_VIDEO_DESK/일러스트_공유허브_경로설정.bat`.
5. 패널 실행 → 관리 > **환경 점검** 전부 PASS 확인.
6. 이 PC는 **pull only**: `CODEX_VIDEO_DESK/수신PC_자동업데이트_켜기.bat`. 패널 "GitHub 업로드" 사용 금지(STEP 0-2).
7. (R1) clasp 로그인은 하지 않음 — 광고 코드 배포는 GitHub Actions가 함(로컬 PC push 경유).
8. Claude: 담당자 계정 Cowork에서 이 리포 폴더 선택 → 시작 명령은 `CLAUDE.md` STEP 2·각 task 시작 문구 그대로.

---

## 4. 지식 이전 (읽는 순서)

| 순서 | R1 | R2 |
|---|---|---|
| 1 | `CLAUDE.md` 전체 | `CLAUDE.md` STEP 0·2 |
| 2 | `_docs/SYSTEM_MAP.md` 0번 인덱스 | 같음 |
| 3 | `ads/README_FOR_AI.md` → `ads/MANUAL.md`(매일·주간·월간 운영) | `_docs/CARDNEWS_BUILD.md`, `_docs/INSTRUCTIONS_SHORTS.md` |
| 4 | `_docs/DISASTER_RECOVERY.md` | `CODEX_VIDEO_DESK/PANEL_TASK.md`(패널 사용) |
| 5 | `_docs/TOPIC_ENGINE.md` | `cardnews/templates/article_authoring_spec.md` |

- **[사실] 공백**: 카드뉴스·영상·패널의 **사람용 일일 운영 매뉴얼은 없음**(현 가이드는 Claude 작업용 서술). 광고는 `ads/MANUAL.md` 존재. → §8 D5.

---

## 5. 동행 운영(인수 기간)

- 기간 [결정 D4]. 사장님 동석 → 담당자 단독 → 사장님 검수 순.
- 매 작업 후 기록: 무엇을 했고 어디서 막혔는지 → 막힌 지점은 가이드 보강(문서화 규약 "가이드 박아").

---

## 6. 완료 기준 (담당자 단독 수행, 사장님 검수)

| # | 과제 | R1 | R2 | 확인 방법 |
|---|---|---|---|---|
| 1 | 주제 생성 → 기사 JSON 1건 작성·push 요청 | ○ | ○ | `cardnews/articles/` 신규 파일 + 로컬 PC에서 push |
| 2 | 카드뉴스 1건 렌더 | ○ | ○ | `cardnews/output/<slug>/` 18 JPG |
| 3 | 영상 1편 렌더(이미지 프롬프트→가져오기→렌더) | ○ | ○ | `CODEX_VIDEO_DESK/RESULTS/` mp4 + 렌더 로그 |
| 4 | 관리대장 전체 새로고침 + 토큰 연결 테스트 | ○ | — | 시트 메뉴 결과 ✅ |
| 5 | 텔레그램 수신·명령 | ○ | 수신만 | 아침 브리핑 수신 |
| 6 | 장애 1건 처리(패널 재시작·환경점검 FAIL 해결 등) | ○ | ○ | 처리 기록 |

---

## 7. 권한 회수 (퇴사·역할 변경 시) — 역순

1. GitHub collaborator 제거.
2. Google 시트·Apps Script·Drive·GA4 공유 해제.
3. Meta 비즈니스·네이버·Google Ads 사용자 제거.
4. `listener_config.json`에서 chat_id 제거.
5. **그 사람 PC에 있었던 키 재발급**: Supertone·Gemini·서비스계정 키·(있었다면) 텔레그램 봇 토큰 — 절차 = `DISASTER_RECOVERY.md` "재발급 절차".
6. R1이었다면: Apps Script 스크립트 속성 키(META·NAVER·GOOGLE_ADS·GEMINI·APIFY) 재발급 검토[§2 미확인 항목 때문], GitHub Actions Secrets 중 `CLASPRC_JSON` 재발급(`clasp login` 후 갱신) 검토.
7. 담당자 PC의 `_secrets/` 삭제 확인.

---

## 8. 결정 필요 (사장님)

| # | 질문 | 선택지 |
|---|---|---|
| D1 | 담당자 역할 | R1 운영자 / R2 제작자 |
| D2 | 담당자가 코드를 고칠 일이 있나 | 없음(pull only, 현 STEP 0 유지) / 있음(로컬 PC에서만 작업 또는 PR 방식 도입 — STEP 0 변경 필요) |
| D3 | GitHub Secrets 노출 대응(Write 권한자) | 담당자는 Read만 / Write 부여 + 배포용 별도 Google 계정으로 `CLASPRC_JSON` 교체 / Environment 승인자 지정 |
| D4 | 동행 운영 기간 | N주 |
| D5 | 사람용 운영 매뉴얼(카드뉴스·영상·패널) | 지금 작성 / 동행 기간에 담당자가 작성 |
| D6 | 계정 체계 | 현 개인 Gmail 유지 / 회사 공용 계정(또는 Google Workspace) 도입 후 이전 |

---

## 9. 출처
- 코드·스캔: 이 리포 (2026-10-12 기준), 스캔 = `git rev-list --all --objects` + `git cat-file --batch` 정규식
- [Apps Script 설치형 트리거(공식)](https://developers.google.com/apps-script/guides/triggers/installable) — 만든 사람 권한으로 실행
- [Apps Script Properties Service(공식)](https://developers.google.com/apps-script/reference/properties/) — 스크립트 속성은 그 스크립트의 모든 사용자 공유
- [GitHub Actions secrets(공식)](https://docs.github.com/en/enterprise-server@3.9/actions/security-guides/using-secrets-in-github-actions) — 파일 편집 권한이 있으면 워크플로에서 secrets 사용·읽기 가능
