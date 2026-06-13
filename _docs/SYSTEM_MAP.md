# 폰스팟 시스템 개발 맵 (클로드 수정용 인덱스)

> **목적**: 코드/기능을 고칠 때 **전체를 읽지 않고** 해당 대단원 한 섹션만 읽으면 되도록,
> 기능을 대단원으로 갈라 경로·핵심 함수·"수정 시 읽을 것"·함정을 박아둔 맵.
> **이 파일은 사람용 설명서가 아니라 클로드(개발 세션)용 내비게이션이다.**
>
> 사용법:
> 1. `CLAUDE.md`(하네스 헤드) → STEP 1/2로 작업 유형 파악.
> 2. **코드 수정/디버깅이면 먼저 이 파일에서 해당 대단원(A~J)을 찾는다.**
> 3. 그 단원의 "수정 시 읽을 것"만 Read → 고친다 → "함정" 체크 → 검증.
> 4. 다른 단원 파일은 "교차 영향" 표시가 없으면 읽지 않는다.
>
> 경로 표기: 모두 리포 루트 `phonespot_cardnews/` 기준 상대경로.
> 줄번호는 검증된 것만 표기(변동 가능, 함수명이 1차 기준).
>
> **★ 문서화 규약**: "가이드 박아"는 1회성 요약본 생성이 아니다. `CLAUDE.md`의 "문서화 규약" 절차대로
> = 해당 대단원 섹션 갱신 → 이 파일 변경이력 1줄 → (라우팅 변경 시) CLAUDE.md STEP 1·2·4 + STEP 8 동기화.
> 사실만 박는다. 새 분류면 대단원 신설 + 0번 인덱스 등록.

---

## 0. 대단원 인덱스 (어디를 고치려면 어디로)

| 고치려는 것 | 대단원 |
|---|---|
| 웹 패널 버튼·액션·버전·화면 | **A. 패널** |
| 카드뉴스 1건 수집→발행→렌더 | **B. 카드뉴스 파이프라인** |
| 영상(쇼츠) 빌드·자막·TTS·퍼블리시 | **C. 영상 파이프라인** |
| 일러스트 공유·Drive 허브·백업·중복 | **D. 라이브러리 & 멀티PC 공유** |
| "그림 내용" 기반 매칭·임베딩·개념발굴 | **E. 의미매칭/임베딩** |
| git push/pull·멀티PC 역할·런타임파일 추적 | **F. Git & 멀티PC & 리포 위생** |
| 광고 관리대장·메타/네이버/유튜브 학습·생성기 | **G. 광고 (ads/)** — 별도 정본 가이드로 위임 |
| 텔레그램·outbox·자동화 신호 | **H. 자동화/텔레그램** |
| .bat/.ps1 깨짐·인코딩·줄끝 | **I. 인코딩 & 실행파일 규칙 (교차)** |
| 기사 JSON 작성 기준 (클로드 집필) | **J. 기사 작성 스펙** |

---

## A. 패널 (웹 대시보드)

**목적**: 카드뉴스+영상 생산을 한 화면에서 제어. 단일 파이썬 HTTP 서버 + 인라인 HTML.

**핵심 파일**
- `CODEX_VIDEO_DESK/dashboard/server.py` — 서버 본체. `INDEX_HTML`(r"""…""" 원시문자열)에 화면+JS가 통째로 들어있음.
- `CODEX_VIDEO_DESK/dashboard/start_hidden.ps1` — 패널 기동 런처(숨김 실행). **버전 게이트**가 여기.
- `CODEX_VIDEO_DESK/dashboard/auto_update.cmd` — (수신PC 옵트인) 기동 시 `git pull --ff-only`.
- `CODEX_VIDEO_DESK/dashboard/remote_queue.py` — 원격 렌더 잡 큐.
- `CODEX_VIDEO_DESK/dashboard/stop_panel.ps1` / `run_library_backup.cmd` — 보조.
- 진입 bat: `CODEX_VIDEO_DESK/00_PHONE_SPOT_PANEL.bat`.

**핵심 심볼 (server.py, 검증된 줄)**
- `PANEL_VERSION = "phonespot-web-v24"` (L41) — **버전 단일 출처(SSOT)**. ps1이 이 값을 읽음.
- `get_video_slugs()` (L336) — 영상 슬러그 목록. `list_slugs.py` 호출(articles∪output 독립 스캔).
- `get_cardnews_rows()` (L1073) — 카드뉴스 행. `CARD_OUTPUT ∪ CARD_IMAGES ∪ CARD_ARTICLES` 합집합 스캔.
- 액션 디스패치: `if action == "..."` 블록들 (L1589~2010). 주요:
  - `producer_check`(L1627)=환경 점검 / `delete_slug`(L1636·1876)=슬러그 삭제
  - `system_upload`(L1932)=GitHub 커밋·push / `system_update`(L1939)=의존성 업데이트
  - `library_sync`(L1600)·`library_dedup`(L1609)·`library_backup`(L1618)
  - `video_prepare`·`video_import_propose/confirm`·`video_render_selected`·`card_*`·`update_visual`·`adjust_chunk`·`set_section_chunks`·`telegram_*`
- 환경점검 버튼 UI: L2172 근처. deleteSlug() JS: L2633·2655 근처.

**버전 게이트 동작 (start_hidden.ps1)**
- ps1이 server.py에서 정규식 `PANEL_VERSION\s*=\s*"([^"]+)"` 로 버전을 읽어 표시(폴백 "phonespot-web-v21").
- **화면이 안 바뀌면 server.py의 `PANEL_VERSION`만 올리면 됨.** ps1엔 손 안 댐.

**수정 시 읽을 것**
- 버튼/액션 추가·변경: `server.py`의 `INDEX_HTML`(버튼 HTML+JS) + 액션 디스패치 블록.
- 화면만: `INDEX_HTML`.
- 기동/버전: `start_hidden.ps1` + `PANEL_VERSION`.

**함정**
- `INDEX_HTML`은 거대한 raw string → Edit 부분일치 truncation 주의(I 단원). 긴 변경은 통째 Write 검토.
- `start_hidden.ps1`은 **ASCII 주석만**(BOM 없는 PS는 CP949 오독으로 깨짐).
- 액션 추가 시 GET(`json_response`)와 POST(`/api/action`) 양쪽 정합 확인.

**교차 영향**: 렌더/라이브러리/슬러그 액션은 C·D 단원 스크립트를 subprocess로 부름.

---

## B. 카드뉴스 파이프라인 (수집 → 발행 → 렌더)

**목적**: 주제 수집 → 기사 JSON → 캡션/프롬프트 → 18 JPG 렌더.

**핵심 경로**
- `cardnews/articles/NNN_<type>_<topic>.json` — 기사(주제) 정본. **git 추적**(중복방지 DB 겸 부사수 배포 매개).
- `cardnews/images/<slug>/prompt.md + 1~5.png` — GPT 카드이미지(영상 배경 base).
- `cardnews/output/<slug>/` — 18 JPG + captions.md(렌더 결과).
- `cardnews/templates/caption_template.md` — 5채널 카피·캡션·후킹 룰.
- `cardnews/templates/article_authoring_spec.md` — 기사 JSON 작성 기준(→ J 단원).
- `cardnews/webui/app.py` (`webui/start.bat`) — Flask 컨트롤 패널.
- `cardnews/run_pngs.bat` — 슬러그 셀렉트 + 18 JPG 렌더.
- `cardnews/_state/content_guide.md` — 사이클 학습 메모(존재 시).

**마스터 룰 문서**
- `_docs/INSTRUCTIONS_CARDNEWS.md` — 시스템·수집·발행 마스터.
- `_docs/CARDNEWS_BUILD.md` — 1건 빌드 워크플로 (수집→JSON→prompt.md→이미지→렌더→발행 9단계).
- `_docs/INSIGHTS_LOOP.md` — 시트(유튜브_인사이트 + 메타_인사이트) → 클로드 누적 학습 루프. 시트 직접 Read 단일 모델(코덱스·GitHub·Drive MD·mklink 다 폐기). 매 사이클마다 새로 Read = 시간 갈수록 후보·후킹 정교화.
- `cardnews/templates/caption_template.md` — 5채널 + 영상 나레이션(채널 6, run_pngs 시 captions.md 자동 append) 첫 줄 후킹 분담 표준.

**후보 가중치 라벨 매트릭스 (수집 단계, INSIGHTS_LOOP.md §3 정본)**
- `yt+30%` 유튜브_인사이트 Top 10 키워드 매칭 / `yt-hook+20%` Top 5 후킹 패턴(숫자포함·의문문 등) 적용
- `meta+20%` 메타_인사이트 Top 헤드라인 패턴 / `meta+30%` 우수 광고 컨셉 직접 매칭
- **`store-active+30%`** ★ 시트 채널 운영 시트(메타·당근·카카오·네이버·스레드·인스타) 최근 7일 "진행사항/수정" 메모에 박힌 현재 캠페인 키워드 매칭. 매장 자체 광고 진행=정합 최강
- `season+30%` caption_template.md §6 시즌 핫토픽 / `freshness+10%` 검증된 D-7 이내
- `dup-100%` `cardnews/articles/*.json`에 동일 토픽 이미 발행 → 즉시 제외(강제)
- 회피 키워드(통합요금제·요금 인하·알뜰폰 등) = 표기 후 사장님 판단

**수정 시 읽을 것**
- 캡션/카피 룰: `caption_template.md` + `INSTRUCTIONS_CARDNEWS.md`.
- 렌더 자체: `cardnews/scripts/` + `run_pngs.bat`.
- 후보 수집 가중치: `INSIGHTS_LOOP.md` §3 (정본) + `INSTRUCTIONS_CARDNEWS.md` 자체학습 섹션.
- 발행 완료 통지: H 단원 outbox `<NNN>_ready.txt` 표준.

**함정**
- articles는 git 추적이므로 새 기사 = 중복토픽 회피 대상(`articles/*.json` Glob 먼저).
- 발행 신호는 H 단원(outbox)과 연동.
- **시트 운영 메모 7일 스캔 빼먹으면 매장 핵심 캠페인 누락**(예: 삼성 페스티벌 같은 핫이슈 = WebSearch만 하면 못 잡음, 시트 채널 비고란이 진짜 단서). `store-active+30%` 강제 후보 룰은 INSIGHTS_LOOP.md §5 자가검증에 박힘.
- 시트 sync(sync_sources) 안 들어오면 "인사이트 0건, 가중치 미적용" 1줄 명시 후 진행(다운그레이드 X).
- 메타_인사이트 시트 = 사장님 셋업 대기 중(현재 Drive MD 저장 → 시트 이전 필요). 그 전에는 메타 가중치 0건.

---

## C. 영상(쇼츠) 파이프라인

**목적**: 기사 cards(=영상 대본) → `shorts_script.json` → 일러스트 매칭 → Remotion 렌더 → 퍼블리시 패키지.

**핵심 스크립트 (`shorts/scripts/`)**
- `list_slugs.py` — 슬러그 목록. **articles ∪ output 독립 스캔**(영상이 카드뉴스 없이도 주제만으로 잡음). 플래그 `[OK]`=cards≥2 / `[SC]`=shorts_script 존재 / `[--]`=둘 다 없음. `get_slug.py`=번호→슬러그.
- `build_script.py` — articles/<slug>.json → `cardnews/output/<slug>/shorts_script.json`.
  - `pick_images(n)`: 카드이미지 없으면 `[""]*n` 반환(과거 sys.exit → 폐기). `ILLUST_PLACEHOLDER="smartphone"`.
  - `build_chunk_visuals()`: 이미지풀 비면 청크마다 `{"type":"illust","value":ILLUST_PLACEHOLDER}` → 렌더의 semantic match가 실제 일러스트로 교체.
  - 구스키마 감지/재생성: `_is_outdated()`. 마커 `_chunk_logic_v2`.
- `codex_prepare_illustrations.py` — 준비 오케스트레이터. 순서: `build_script` → `codex_enhance_script` → `codex_apply_uploaded_illustrations` → `codex_illustration_scout` → `codex_concept_scout`(optional) → `codex_refresh_workbench` → LATEST_PROMPT 열기.
- `codex_enhance_script.py` — 스크립트 보강. `codex_caption_lockstep.py` — 자막·TTS 동기.
- `codex_semantic_visual_match.py` — **렌더 Step 3: 청크 텍스트↔일러스트 의미매칭**(→ E 단원).
- `publish_codex_package.py` — 결과 패키지 + 유튜브 메타.
  - `clean_title()`: 이모지(`_TITLE_EMOJI`) + 장식 괄호(`_TITLE_DECOR_BRACKETS=【】〔〕「」『』《》〈〉［］｛｝`) 제거, `?! ~ . ( )`는 유지.
  - `strip_youtube_extra_sections()`/`clean_youtube_description()`: 타임스탬프·핵심데이터·출처 제거.
- 기타: `codex_chunk_overrides.py`(청크 수동분할), `codex_clean_latest_prompt.py`, `codex_refresh_workbench.py`, `validate_codex_korean.py`, `verify_video_quality.py`.

**렌더 엔진**
- Remotion: `shorts/` + `render_remotion_fast.mjs`(브라우저 자동탐색 `ensureBrowser`+`findLocalChrome`, Playwright chromium/시스템 Chrome 폴백).
- 진입 bat: `run_codex_casual.bat`(CLI 폴백에서 `--concurrency` 제거됨 — "%" 깨짐 방지).
- 트랙 구분: casual/newsroom(카드뉴스 영상) vs `shorts/promo/`(타이포 홍보) vs `shorts/promo_ai/`(실사 AI 광고, Higgsfield).

**마스터 룰 문서**
- `_docs/INSTRUCTIONS_SHORTS.md`(주의: 옛 MoviePy/Typecast 설계 잔존, 현행 Remotion과 일부 불일치).
- `CODEX_VIDEO_DESK/README.txt`, `CODEX_VIDEO_DESK/MAINTENANCE/CODEX_MASTER_VIDEO_GUIDE.md`.

**수정 시 읽을 것**
- 스크립트 생성 로직: `build_script.py`만.
- 자막 타이밍/동기: `codex_caption_lockstep.py` + `codex_enhance_script.py`.
- 일러스트 매칭 품질: E 단원.
- 유튜브 제목/설명: `publish_codex_package.py`.

**함정**
- 카드이미지 없는 슬러그 = 일러스트 전용 모드(정상). build_script가 막지 않음.
- `shorts_script.json`은 **런타임 생성물 → git 비추적**(F 단원). 손폴리시본(_auto_generated=False)은 재생성 보존.

---

## D. 라이브러리 & 멀티PC 일러스트 공유

**목적**: 일러스트 자산을 PC 간 공유. **대량 이미지는 MCP base64 부적합 → Google Drive 데스크톱 허브가 정답.**

**핵심 경로/스크립트**
- 허브: Google Drive 데스크톱 공유폴더 `PhoneSpot_Library`(데스크톱 동기).
- 경로파일: `shorts/config/library_share_path.txt` (예: `G:\내 드라이브\PhoneSpot_Library`). **git 제외, PC별 다름.**
- `shorts/scripts/codex_library_sync.py` — 양방향 비파괴 병합(`--dry-run` 미리보기). **렌더 직전 워커가 best-effort 자동 호출**(`RENDER_WORKER/worker.py`).
- `shorts/scripts/codex_detect_drive_hub.py` — Drive 로컬경로 자동탐지("내 드라이브\PhoneSpot_Library" / "My Drive\…") → 경로파일 기록.
- `shorts/scripts/codex_library_dedup.py` — 중복 탐지/병합(`--apply`, 임계 `PHONESPOT_DEDUP_SIM`).
- `shorts/scripts/codex_library_backup.py` — 스냅샷(회전 기본 10).
- 자산 위치: `shorts/public/assets/illustrations/*.png`(런타임, git 비추적), 태그DB `shorts/config/illustration_tag_db.json`.

**런처 bat (CODEX_VIDEO_DESK/)**
- `라이브러리_공유_동기화.bat` / `라이브러리_중복정리.bat` / `라이브러리_백업.bat`
- `라이브러리_자동백업_스케줄_등록.bat`(매일 09:00) / `…_해제.bat`
- `일러스트_공유허브_경로설정.bat`(자동탐지 우선, PC별 1회)
- 패널: "관리 > 라이브러리 동기화" 버튼(액션 `library_sync` 등).

**마스터 룰 문서**
- `CODEX_VIDEO_DESK/MAINTENANCE/MULTI_PC_STANDALONE_AND_LIBRARY_SHARING_GUIDE.md`.

**수정 시 읽을 것**
- 동기화 병합 로직: `codex_library_sync.py`만.
- Drive 경로 탐지: `codex_detect_drive_hub.py`.

**함정**
- 허브 경로파일은 git 비추적 → 새 PC마다 설정 필요.
- 동기화는 비파괴 병합(삭제 X). 중복정리는 `--apply` 줘야 실삭제.

---

## E. 의미매칭 / 임베딩 엔진

**목적**: 청크 텍스트의 **그림 내용** 기준으로 라이브러리 일러스트를 매칭(파일명/태그가 아니라 의미).

**핵심 스크립트 (`shorts/scripts/`)**
- `codex_semantic_visual_match.py` — 렌더 단계 매칭 본체(텍스트→일러스트). 폴백 `NEUTRAL_FILLERS`.
- `codex_illust_embed.py` / `codex_image_embed.py` — 텍스트/이미지 임베딩(jina-clip 계열).
- `codex_illust_match_preview.py` — 읽기전용 의미매칭 미리보기.
- `codex_concept_scout.py` — **개념 발굴형 스카우트**: 라이브러리에 없는 갭을 범용 개념으로 발굴.
  - `readable_variant()`: Gemini 번역으로 `<english_slug>_<hash8>` 사람읽기 이름. 키 없으면 `cpt_<hash8>` 폴백.
  - 캐시 `shorts/config/concept_name_cache.json`(git 비추적). 키파일 `_secrets/gemini_key.txt`.
- `codex_illustration_scout.py` / `codex_illustration_db.py` / `codex_unique_illustration_guard.py` / `codex_warm_embeddings.py`.
- 지문/사용이력: `shorts/codex/ILLUSTRATION_TAG_DB.md`, `shorts/codex/illustration_usage_history.json`(런타임, git 비추적).

**수정 시 읽을 것**
- 매칭 알고리즘: `codex_semantic_visual_match.py` (+ embed 모듈).
- 개념 발굴/이름: `codex_concept_scout.py`.

**함정**
- 임베딩 모델 ~1GB. 설치/워밍은 `SETUP_FULL_PRODUCER.bat` / `codex_warm_embeddings.py`.
- Gemini 키 없으면 readable 이름 폴백(cpt_) — 에러 아님.

---

## F. Git & 멀티PC 역할 & 리포 위생  ★ 이번 세션 핵심 변경

**머신 역할 (CLAUDE.md STEP 0이 최우선)**
- **노트북**(`C:\Users\di898\Documents\phonespot_cardnews`) = 개발. **push only**. — 이 세션이 돌아간 PC.
- **실행 PC / 부사수**(`C:\PhoneSpot\phonespot_cardnews`) = 생산. **pull only**.
- **메인 PC**(192.168.0.7) = 카드 이미지 원본 자산.
- 원칙: 노트북 수정 → push → 실행 PC pull → 실행 PC에서 실행. **push는 노트북에서만**(다중 writer 분기 방지).

**git 실행파일 탐색 (★ 이번 세션 수정의 핵심)**
- 이 환경엔 Git for Windows가 **설치 안 됨**. git은 **GitHub Desktop 내장본**만 존재:
  `%LOCALAPPDATA%\GitHubDesktop\app-*\resources\app\git\cmd\git.exe` (현재 app-3.5.12).
- 패널 파이썬(`MAINTENANCE/codex_github_upload.py`의 `find_git()`)은 PATH→`C:\Program Files\Git`→GitHub Desktop glob 순으로 찾아 **정상 작동**.
- **bat의 git 탐색은 cmd `dir`로 경로 중간 와일드카드(`app-*\…`)를 못 푼다.** 반드시 아래 패턴 사용:
  ```bat
  set "GIT="
  where git >nul 2>&1 && set "GIT=git"
  if not defined GIT if exist "C:\Program Files\Git\cmd\git.exe" set "GIT=C:\Program Files\Git\cmd\git.exe"
  if not defined GIT if exist "C:\Program Files\Git\bin\git.exe" set "GIT=C:\Program Files\Git\bin\git.exe"
  if not defined GIT for /d %%D in ("%LOCALAPPDATA%\GitHubDesktop\app-*") do if exist "%%D\resources\app\git\cmd\git.exe" set "GIT=%%D\resources\app\git\cmd\git.exe"
  if not defined GIT ( echo [ERROR] git not found. & pause & exit /b 1 )
  ```
  이후 모든 git 호출은 `"!GIT!"` (요구: `setlocal enabledelayedexpansion`).
  **`dir /b /s "...app-*\resources\...git.exe"` 패턴은 금지**(항상 빈 결과 → "git not found" 오진).

**push/pull bat (위 GIT 패턴 적용 완료)**
- `CODEX_VIDEO_DESK/런타임파일_git정리_1회.bat` — **런타임 생성물 git 추적 해제(1회, 메인/노트북)**. `git rm --cached` 후 commit → `pull --no-rebase --no-edit` → push.
- `CODEX_VIDEO_DESK/기사_깃에_올리기.bat` — articles+.gitignore push(pull→push).
- `노트북_깃허브_올리기.bat`(리포 루트) — 노트북 전용 `git add -A`+commit+push.
- `CODEX_VIDEO_DESK/부사수PC_원클릭_셋업.bat` — 빈 PC 1파일: winget git/node/python → clone(stash 후 pull) → `SETUP_FULL_PRODUCER` → Drive Y/N. UNC 경로 가드.

**자동 업데이트 (수신PC 옵트인)**
- 마커: `CODEX_VIDEO_DESK/TEMP/panel/auto_update.on`.
- 켜기/끄기: `수신PC_자동업데이트_켜기.bat`/`끄기.bat`(구호환 `2번째PC_자동업데이트_켜기.bat`).
- 패널 기동 시 `dashboard/auto_update.cmd`가 `git stash --include-untracked` → `git pull --ff-only`(항상 exit 0, 패널 안 막음).

**런타임 파일 git 비추적 (★ "가만히 있어도 M 뜨는" 원인 차단)**
- 패널/렌더/동기화가 계속 재생성하는 git 추적 파일이 가짜 M·pull충돌의 뿌리.
- `.gitignore`에 추가(이미 반영): `shorts/config/illustration_tag_db.json`, `shorts/codex/ILLUSTRATION_TAG_DB.md`, `shorts/codex/illustration_usage_history.json`, `shorts/public/shorts_script.json`, `shorts/public/assets/illustrations/`, `shorts/config/library_share_path.txt`, `shorts/config/concept_name_cache.json`. **un-ignore**: `cardnews/articles/`.
- 적용 = `런타임파일_git정리_1회.bat` 1회 실행(메인/노트북). 이후 그 파일들 재생성돼도 git이 안 잡음.

**git 전파 vs 비전파**
- 전파(코드 허브): 코드·`.bat/.ps1/.mjs`·`cardnews/articles/*.json`·가이드·`.gitattributes`.
- 비전파(Drive/LAN/셋업으로 따로): `cardnews/images`·`output`·`_secrets`·`node_modules`·임베딩·런타임 생성물·`library_share_path.txt`.

**GitHub 연동 스크립트 (`MAINTENANCE/`)**
- `codex_github_upload.py`(add→commit→pull→push, 로그 `TEMP/github_upload.log`), `codex_github_update.py`(의존성), `codex_github_status.py`. 셋 다 `find_git()` 보유.

**수정 시 읽을 것**
- 새 git bat 만들 때: **이 단원의 GIT 패턴만** 복붙 + I 단원 인코딩 규칙.
- push 실패: `TEMP/github_upload.log` + 머신 역할(노트북만 push).

**함정**
- 노트북엔 Git for Windows가 없음 → "git not found"는 보통 **bat 탐색 코드 문제**지 미설치가 아님. 먼저 GitHub Desktop 경로 확인.
- 실행 PC에서 push 금지(분기). 막히면 `git fetch origin && git reset --hard origin/main`(gitignore 자산 안 건드림).

---

## G. 광고 관리대장 (ads/, ads_kt/) — 별도 정본으로 위임

**목적**: 폰스팟/KT 광고 KPI·메타/네이버/유튜브 자동화·광고소재 생성기. **이 맵은 포인터만**; 상세는 ads 자체 정본 가이드.

**진입/정본**
- `ads/README_FOR_AI.md`(Sheet ID + 자동화 흐름) → `ads/MANUAL.md`(운영).
- **광고 생성기 단일 정본**: `ads/IMPLEMENTATION_GUIDE_2026-06-09.md`(§0 최신 아키텍처 → §5/§6 함수 인덱스 → §11~14).
- 학습 루프: `ads/YOUTUBE_LEARNING.md` / `ads/META_LEARNING.md` / `ads/NAVER_AUTOMATION.md` / `ads/SNS_AUTOMATION_ROADMAP.md`.
- KT: `ads_kt/README_FOR_AI.md`.

**핵심 코드**
- Apps Script: `ads/code/apps_script/Code.gs`, `meta-sync.gs`, `naver-sync.gs`, `generator.html`, `styles.html`(include 패턴 폐기, 참고용).
- 자동화: 메타 01:30 syncAll + 01:45 인사이트 MD / 인스타 02:00 / 네이버 02:15 / GA4는 syncAll 내장.

**함정 (운영 룰)**
- Apps Script 코드는 **함수 단위로 박을 것. 통째 교체 금지**(인사이트 함수 누락 사고 재발 방지).
- `generator.html`은 큰 Edit 누적 시 끝부분 잘림(18회+). **다음 큰 변경은 통째 Write**. 백업본 `ads/code/apps_script/generator.v_*.html`.
- 시트 라벨링(카테고리/후킹/지역 컬럼) 안 하면 매칭 0건.
- **Apps Script는 git pull로 자동 반영 안 됨**(웹 배포 별도).

**2026-06-12 세션2 — 생성기 핵심 (상세 = `ads/IMPLEMENTATION_GUIDE_2026-06-09.md` §0-1 + `CLAUDE.md` STEP8)**
- 결과 = 🎲 8행 랜덤 변주(후킹×톤 1:1 조합) → ✨라이브러리 → 🎯벤치마크. `buildCopyPrompt` 4단(목적/지정값/규칙/출력), 단일조합=한 방향 강제(행별 12개).
- **1:1 매핑**: `buildCopyPrompt` base에서 라이브러리·벤치마크 제거 → `buildLibraryEnrichedPrompt`/`buildBenchmarkEnrichedPrompt`가 `# 출력 양식` 앞에 자기 참고만 주입. `buildImagePrompt(ctx,tone,layout,refMode)`도 동일('none'/'library'/'benchmark'/'both').
- 이미지 = 완성 배너(헤드라인+CTA+스티커, 한글 in-image) + 아트디렉션 랜덤(`AD_STYLE_POOL` 12종). 슬로건→이미지 = `copyImageWithHeadline`(변주박스 `#img-headline`).
- 지역·신규컨셉 = 모든 카피 무조건 반영(`regionEmphasis`/`conceptEmphasis`, 앵글을 후킹 중심). 길이=`lengthRule`(특정 선택 시 통일·자유만 분포), 타겟=`targetRule`(특정 세대·성별 시 어휘·말투 밀착).
- 신규 상수: `ALL_TONES_V`/`ALL_HOOKS_V`/`TONE_STYLE_V`/`HOOK_STYLE_V`/`HOOK_PATTERN_HINT`/`TONE_HOOK_EQUIV`/`AD_STYLE_POOL`. 신규 함수: `drawVariationCombos`·`renderVariations`·`copyVariation*`·`copyBoxImagePrompt_`·`requestSemanticMatch`·`setSemanticLoading`.
- **Gemini 의미매칭** (대단원 E와 별개, ads 전용): `getSemanticAdMatches`(meta-sync.gs) ↔ `requestSemanticMatch`/`searchLibraryMatching`/`searchBenchmarkMatching`(generator). 컨셉/지역 앵글로 주제 유사 광고 추천(카테고리 무관, 임계 55). **함정: GEMINI_API_KEY + 배포 웹앱 필요**, 외부 URL 모드는 스킵. 빠른 연속 생성 시 콜백 레이스 가드 없음.
- **함정**: 지역+컨셉+무조건이 겹치면 카피 과제약(빡빡)·LLM 일부 무시 가능 → 실사용 다이얼 필요. bash 마운트는 폴더 연결 시점에 frozen → 편집 검증은 **호스트 Read + outputs 마운트로 JS 떼어 `node --check`**.

**2026-06-11 세션 — 광고운영 자동화 확장 (광고운영 task, 상세 = `ads/` 가이드 5종)**
- **통합대시보드 자동 합산 패치**: `Code.gs` `updateChannelMatrixWithGA4` + `updateKPISummary` + `addTimeSeriesChart`. `channels`/`ADS`/`trendChannels` 배열에 `adSheet`/`impCol`/`clkCol`/`spdCol` 분리 → 메타→`메타_통합`(H 지출), 네이버→`네이버_통합`(H 지출). 기타 채널(구글/카카오/당근)은 기존 E/F/G 그대로 = 다운그레이드 없음.
- **인스타 자동화 완료**: `meta-sync.gs` `syncInstagramDaily()` 매일 02:00. `INSTAGRAM_BUSINESS_ID=17841474706647015` (@phonespot.kr). **함정: 메타 시스템 사용자 토큰 scopes는 발급 시점에 확정 — 기존 토큰에 자산 추가만으로 권한 안 늘어남. 새 토큰 발급 필요.** 가이드 = `ads/INSTAGRAM_AUTOMATION_PENDING.md`(완료 헤더).
- **네이버 검색광고 자동화 완료**: `naver-sync.gs` `syncNaverIntegrated()` 매일 02:15. HMAC-SHA256 인증. **API 함정**: ①`/stats` 호출 시 `statType` 파라미터 자체를 **빼야 함**(ADGROUP/AD/AD_DETAIL 등 다 400 거부) ②`ids`는 **콤마 구분 문자열**(`adgroupIds.join(',')`), JSON 배열 거부. KT 자동 제외 = 캠페인명 'KT'/'다이렉트샵' 포함 필터. 가이드 = `ads/NAVER_AUTOMATION.md`.
- **`generateMetaInsightsMarkdown` 누락 사고 + 복구**: meta-sync.gs 통째 교체 시 인사이트 패치 함수 사라짐 → 매일 01:45 트리거 catch 안 됨 → refreshAll `is not defined` 에러. 복구: `outputs/meta_insights_patch.js` 통째 박기. **위 "함정"의 "함수 단위로 박을 것" 룰 그대로**.
- **카카오톡 채널 자동수집 불가 확정**: developers.kakao.com 도구 페이지에 채널 통계 조회 API 없음. 일반 비즈니스 채널 인증으로 자동수집 불가. 수기 입력 유지.
- **스레드 자동화 보류**: 메타 비즈매니저 시스템 사용자 자산 추가 화면에 Threads 옵션 없음 → Threads API가 시스템 사용자 토큰 모델 미지원 추정. 대안: 별도 앱+개인 OAuth 또는 메타 정책 변경 대기.
- **SNS 자동화 가능성 매트릭스 신설**: `ads/SNS_AUTOMATION_ROADMAP.md`. 콘텐츠 채널(유튜브 완료/인스타 완료/스레드 보류/틱톡 미정/네이버블로그·카페 API없음) + 광고 채널(메타 완료/네이버 완료/구글·카카오 가능/당근 API없음).
- **멀티 브랜드 모노레포 제안**: 신설 `ads/MULTI_BRAND_ARCHITECTURE.md`. `_shared/`(공용 코드 = `apps_script/`+`cardnews/`+`shorts/`+`automation/`) + `brands/<brand>/`(데이터·설정 분리, `config.json`+`.clasp.json`+`articles/`+`images/`+`output/`) + clasp+GitHub. **Phase 1**(Apps Script만 멀티 배포) 다른 task `generator.html` 작업 종료 후 시작. KT/국민인터넷/진짜 폰스팟(판매점 가입형) 등 확장 대비. **충돌 방지 = 책임 분담 표** (gen.html=다른 task / Code.gs·meta-sync·naver-sync=광고운영 task / cardnews·shorts=영상 task).

---

## H. 자동화 / 텔레그램 / outbox

**목적**: 폰↔PC 명령, 발행 신호 큐.

**핵심 경로**
- `automation/scripts/telegram_listener.py` — 폰→PC 명령 + outbox 자동 푸시(매 폴 사이클 끝 `check_outbox(trusted)`).
- `automation/scripts/tg_send.py` — 1회 송신 CLI(`from tg_send import send_text` 모듈 사용 + `py -3 tg_send.py <txt_path>` CLI).
- `_state/outbox/*.txt` — 클로드가 떨군 송신 큐 / `_state/outbox_sent/` — 완료 보관(4096자 초과 시 3800자 청크 분할 + `[N/M]` 프리픽스).
- 마스터: `_docs/AUTOMATION_OVERVIEW.md`(webui·listener·outbox·run_pngs 매커니즘).

**클로드 outbox 파일명 표준**
- 신규 수집 후보표: `<YYYY-MM-DD>_collect.txt` (또는 `_collect_v2.txt`, `_collect_numbered.txt`). 풀 후보 + 가중치 라벨 + 정직한 한계 포함.
- 카드뉴스 작성 완료 통지: `<NNN>_ready.txt` 또는 `<NNN>_<NNN>_<NNN>_ready.txt` (일괄). slug + title + 산출물 경로 + 사장님 다음 단계 포함.
- PING/디버그: `ping_test.txt`.
- 송신 성공 시 자동 `_state/outbox_sent/`로 이동. 실패 시 outbox에 잔존(다음 사이클 재시도).

**수정 시 읽을 것**: `AUTOMATION_OVERVIEW.md` + 해당 스크립트.

**함정**
- listener 죽으면 outbox 쌓이기만 함(데이터 손실 X, 재시작 시 한 번에 푸시). 부팅 자동시작 = `shell:startup`에 `start_listener_silent.vbs` 바로가기(1회 셋업).
- 송신 성공 = `resp_ok=True + message_id` 로그 확인(`automation/_state/listener_log.txt`). 폰 미수신 시 봇 채팅창·알림 mute·차단 점검.

---

## I. 인코딩 & 실행파일 규칙 (★ 교차, 모든 .bat/.ps1 작업 시 필수)

**.bat 규칙 (절대)**
- **NO BOM + ASCII 본문 + CRLF.** cmd.exe는 .bat의 UTF-8 BOM 미지원(→ `@echo off`가 `癤?echo`로 깨짐).
- **본문에 한글 금지**(BOM 없으면 CP949 오독). **파일명은 한글 OK.**
- bat이 만드는 출력 파일명·echo 문구도 ASCII(한글 파일명 참조 echo도 깨짐).
- 한글이 꼭 필요한 내용 bat은 UTF-8 BOM 필수 + `chcp 65001` — 단, 그 경우 ASCII화가 더 안전.

**.ps1 규칙**
- `start_hidden.ps1`은 **ASCII 주석만**(BOM 없는 PS는 CP949 오독).

**편집 절차 (truncation 회피)**
- `.bat/.ps1`·거대 raw string(server.py INDEX_HTML)·`generator.html`은 Edit 부분일치 truncation 위험.
- 편집 후 **반드시 검증**: BOM 없음 / nonASCII 본문 0 / CRLF. 검증 스니펫(workspace bash, 마운트 경로):
  ```python
  b=open(p,'rb').read(); bom=b[:3]==b'\xef\xbb\xbf'
  if bom: b=b[3:]
  s=b.decode('utf-8','replace').replace('\r\n','\n').replace('\r','\n').replace('\n','\r\n')
  open(p,'wb').write(s.encode())  # 정규화
  body=s.replace('\r\n','\n'); print(bom, sum(c>'\x7f' for c in body))  # bom=False, count=0 목표
  ```
- 마운트 tearing: bash가 큰/방금-편집 파일을 잘린 사본으로 보일 수 있음 → 호스트 Read로 진본 확인, 잘린 조각만 떼어 `node --check`/스니펫 테스트.

**리포 위생 (STEP 7)**
- 실행파일 단일 위치(SSOT), 루트 편의복사 금지. 새/수정 `.bat/.ps1` 커밋 전 중복 md5 점검.
- `.gitattributes`로 줄끝 고정 + 한글 bat BOM 정책.

---

## J. 기사 작성 스펙 (클로드 집필)

**목적**: 클로드가 주제선정→사실수집→기사 JSON을 일관되게 작성.

**정본**
- `cardnews/templates/article_authoring_spec.md` — cards 텍스트=영상 대본. 출력 분기: 영상(일러스트 자동매칭, 카드이미지 불필요) vs 카드뉴스(+카드이미지).
- 진입: CLAUDE.md STEP 2 "기사 써줘/주제 뽑아줘".

**함정**
- 기사 JSON은 git 추적 = 중복방지 DB. 새 주제는 `cardnews/articles/*.json` 중복 회피 먼저.

---

## 변경 이력 (이 맵 자체)
- 2026-06-13: **B 단원 인사이트 누적 학습 + 가중치 라벨 매트릭스 박음.** 마스터 룰 문서에 `_docs/INSIGHTS_LOOP.md`(시트 직접 Read 단일 모델 — 코덱스·GitHub·Drive MD·mklink 폐기) + `cardnews/templates/caption_template.md`(5채널+영상 나레이션) 명시. 가중치 라벨 6종(yt+30/yt-hook+20/meta+20·30/store-active+30/season+30/freshness+10/dup-100) 정본 위치 = `INSIGHTS_LOOP.md` §3. 함정에 "시트 운영 메모 7일 스캔 빼먹으면 매장 핵심 캠페인 누락(예: 삼성 페스티벌)" 박음. H 단원 outbox 파일명 표준(`<YYYY-MM-DD>_collect*.txt` 후보표 / `<NNN>_ready.txt` 작성 완료 통지) + listener 함정(부팅 자동시작·송신 검증) 박음.
- 2026-06-13: **문서화 규약 박음** — "가이드 박아"는 이 3층 구조(헤드→SYSTEM_MAP 대단원→마스터 가이드)에 합류시키는 것이지 1회성 요약본 생성이 아님. 절차 정본 = CLAUDE.md "문서화 규약" 절. 헤드+이 파일 상단에 동시 명시.
- 2026-06-13: 신설. 이번 세션 git-bat 탐색 수정(F 단원: GitHub Desktop 내장 git을 `for /d`로 탐색, `dir app-*` 패턴 금지) + 런타임파일 git 비추적 + 인코딩 규칙(I)을 대단원으로 정리. CLAUDE.md STEP 1에 "수정 작업 인덱스"로 등록.
- 2026-06-12 (세션2 합류): 대단원 G에 광고 생성기 대개편 핵심+함정 박음 — 8행 변주엔진·1:1매핑·이미지배너+랜덤아트·지역/컨셉 무조건반영·길이/타겟 실반영·Gemini 의미매칭(`getSemanticAdMatches`)·슬로건→이미지(`copyImageWithHeadline`). 정본 상세 = IMPLEMENTATION_GUIDE §0-1, 변경이력 = CLAUDE.md STEP8.
- 2026-06-11 (광고운영 task 합류): 대단원 G에 6/11 세션 블록 박음 — 통합대시보드 자동 합산 패치(`Code.gs` `updateChannelMatrixWithGA4`+`updateKPISummary`+`addTimeSeriesChart` 시트 매핑 분리), 인스타/네이버 자동화 완료, `generateMetaInsightsMarkdown` 누락 사고 + 복구, 카카오톡 채널 불가/스레드 보류 확정, SNS 자동화 매트릭스(`ads/SNS_AUTOMATION_ROADMAP.md`) 신설, 멀티 브랜드 모노레포 제안(`ads/MULTI_BRAND_ARCHITECTURE.md` 신설 — Phase 1 다른 task `generator.html` 종료 후 시작). 정본 = `ads/META_AUTOMATION.md`·`NAVER_AUTOMATION.md`·`SNS_AUTOMATION_ROADMAP.md`·`INSTAGRAM_AUTOMATION_PENDING.md`·`MULTI_BRAND_ARCHITECTURE.md`. CLAUDE.md STEP 1·2·4·8 동기화.
