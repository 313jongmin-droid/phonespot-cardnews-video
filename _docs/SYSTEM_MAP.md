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

**디자인 토큰 정본** = `server.py INDEX_HTML <style> :root` (색·radius·shadow·transition·Pretendard). 추출 참조 = **`_docs/DESIGN_SYSTEM.md`**(패널·광고 생성기·브랜드 페이지 공용). 값 변경은 server.py에서 → 문서 동기화. server.py 165KB 대형 = CSS 수정 bash-python only(I단원).

**목적**: 카드뉴스+영상 생산을 한 화면에서 제어. 단일 파이썬 HTTP 서버 + 인라인 HTML.

**핵심 파일**
- `CODEX_VIDEO_DESK/dashboard/server.py` — 서버 본체. `INDEX_HTML`(r"""…""" 원시문자열)에 화면+JS가 통째로 들어있음.
- `CODEX_VIDEO_DESK/dashboard/start_hidden.ps1` — 패널 기동 런처(숨김 실행). **버전 게이트**가 여기.
- `CODEX_VIDEO_DESK/dashboard/auto_update.cmd` — (수신PC 옵트인) 기동 시 `git pull --ff-only`.
- `CODEX_VIDEO_DESK/dashboard/remote_queue.py` — 원격 렌더 잡 큐.
- `CODEX_VIDEO_DESK/dashboard/stop_panel.ps1` / `run_library_backup.cmd` — 보조.
- 진입 bat: `CODEX_VIDEO_DESK/00_PHONE_SPOT_PANEL.bat`.

**핵심 심볼 (server.py, 검증된 줄)**
- `PANEL_VERSION = "phonespot-web-v32"` (L41) — **버전 단일 출처(SSOT)**. ps1이 이 값을 읽음. 화면/CSS 바꾸면 이 숫자만 올림.
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

**디자인 시스템 (iOS / Apple HIG, 2026-06-13, v25~v32)** — 전부 `INDEX_HTML`의 `<style>` 블록 안.
- **렌더 방식**: `INDEX_HTML = r"""..."""` 순수 raw string + `html_response(self, INDEX_HTML)` 직접 서빙(.format/f-string 아님) → **CSS 중괄호 안전**.
- **토큰(`:root`)**: 시스템 컬러(`--system-bg #F2F2F7`/`--card-bg`/`--label*` 계층/`--separator rgba(.08)`), 브랜드 주황 `--accent #F74B0B`(blue 아님), `--shadow-subtle/-card/-elevated`, 라운드 `--r-sm~xl`, `--t-fast`. **★ legacy alias**(`--line`/`--orange`/`--ink`/`--muted`/`--bg`/`--r` 등)를 신토큰에 매핑 → 본문 인라인 `var(--line)` 등 그대로 작동(깨짐 방지).
- **폰트**: Pretendard Variable(`<head>`에 `<link>` + `@import` 둘 다, dynamic-subset CDN) + `font-variant-numeric:tabular-nums`. 오프라인이면 시스템 폰트 폴백.
- **레이아웃**: max-width 센터링 제거 → **풀폭 + 좌우 20px 균일 거터**(header/.runtime-strip/main 동일). `main` 그리드 `400px 1fr`.
  - 좌측 슬러그 섹션 = `main > section`만 **`position:sticky; top:80px; align-self:start`**(우측 높이에 안 늘어남), `.list { max-height:calc(100vh-188px) }`.
  - 우측 페어: `.pair`(1fr 1fr) = 상태|로그, `.pair.lopsided`(1.8fr 1fr) = 기록|결과. `align-items:stretch`(박스 높이 맞춤). 마크업에서 두 섹션씩 `<div class="pair">`로 감쌈.
- **슬러그 행 = 2줄 iOS 리스트**: `.row`(grid `38px 1fr auto`) → 번호배지 + `.row-main`(`.slug-name` 줄바꿈 + `.row-sub`) + `.stage-pill`. **번호배지 = `idx+1`**(영상은 `videoItems.forEach((item,idx)=>`; 이전 `item.number`는 undefined로 "defin" 깨짐).
- **상단 4박스(runtime-card)**: 흰 카드 통일, 상태는 값 앞 **컬러 점**(`.runtime-card.good/.bad/.warn b::before { content:"●" }` = 초록/빨강/주황). 배경 틴트 제거.
- **선택영상 배지**: `.action-head{flex-direction:column}` + `.selected-badge{width:100%}` 18px → 제목 아래 전폭 좌측.
- **깊이**: 타일/카드 **테두리 없이 그림자 하나**(`.btn{border:none;box-shadow:shadow-subtle}`, 호버=elevated+accent 링). 주황 절제(flag 등 중립).
- **액션 타일 통일**: `.btn.compact`를 일반 `.btn`과 동일 크기·설명 표시로(예전 `display:none` 폐기).
- **단계적 노출(progressive disclosure, v31~v32)**: 영상작업 기본 화면 = 선택영상 + 1·2·3 핵심 스텝만. 보조 묶음 2개를 **접기 토글**로(둘 다 기본 접힘) → 첫 화면에 상태+로그 노출.
  - 공통 토글 스타일 = **`.foldbar`**(전폭 회색 바 + 가운데 라벨 + `.foldbar-caret` ▾접힘/▴펼침). `보기 · 편집`(`#viewEditToggle`→`#viewEditActions`)과 `라이브러리 · 시스템 관리`(`#manageToggle`→`#manageActions`) **둘 다 동일 UI**.
  - JS: `toggleViewEdit()`/`toggleManage()` — display none↔grid + 캐럿 flip. 보기·편집은 **localStorage `panel.viewEdit`** 로 펼침 상태 기억(부팅 L3046 직후 복원). 관리는 매번 접힘.
  - 접이식 그룹은 `grid-column:1/-1` + 자체 `repeat(3,minmax(160px,1fr))` 서브그리드(7개/관리 버튼).
  - 상단 4박스(runtime-card)는 패딩·폰트·`min-height:0`로 슬림화.
- **롤백**: `CODEX_VIDEO_DESK/dashboard/server.py.bak_pre_ios_20260613`(iOS 이전 = 기존 주황 디자인). `copy /Y ...bak... server.py` 또는 `git checkout -- ...server.py`.

**수정 시 읽을 것**
- 버튼/액션 추가·변경: `server.py`의 `INDEX_HTML`(버튼 HTML+JS) + 액션 디스패치 블록.
- 화면만: `INDEX_HTML`.
- 기동/버전: `start_hidden.ps1` + `PANEL_VERSION`.

**함정**
- **★ Edit 누적이 `INDEX_HTML`/파일 꼬리를 truncate(2026-06-13 실제 발생)** — 큰 raw string을 Edit 툴로 여러 번 고치면 끝부분(main() 등)이 잘려 `'(' was never closed` 컴파일 에러. **권장 작업법**: server.py 대규모 CSS/마크업 변경은 **bash-python read→replace(assert count==1)→write**로(Edit 누적 X), 매번 `python -m py_compile` + `<div>/<section>` 개폐 카운트 + 파일 tail(`main guard`) 확인. 잘렸으면 백업 꼬리(`server.py.bak_pre_ios_20260613`)에서 `rindex(anchor)`로 이어붙여 복구.
- 마운트 tearing: bash가 큰/방금 쓴 server.py를 **잘린 사본으로 읽을 수 있음**(읽은 바이트<stat이면 의심). 진위 판단은 `python3 -c "len(open().read())"` vs stat, 또는 호스트 Read. 단 호스트 Read도 **stale 캐시**일 수 있으니 최종 판정은 bash 풀read 바이트수 일치 + py_compile.
- `start_hidden.ps1`은 **ASCII 주석만**(BOM 없는 PS는 CP949 오독으로 깨짐).
- 액션 추가 시 GET(`json_response`)와 POST(`/api/action`) 양쪽 정합 확인.
- 머지 충돌 마커(`<<<<<<< HEAD`)가 `INDEX_HTML` 안에 남으면 Python은 통과(raw string)하지만 화면에 충돌 텍스트·중복 버튼 노출 → 발견 시 정리(이번에 카드 삭제버튼 1개로 통합).

- **렌더 잡 '배정 대기' 고착 = 로컬 워커 readiness 실패(2026-06-18 실증).** 패널 기동 시 `start_local_worker()`가 로컬 워커(`RENDER_WORKER/worker.py`)를 띄우고, 워커는 `readiness()` 의존성 체크를 통과해야만 잡 claim. 하나라도 미설치면 워커는 죽지 않고 **5초마다 재확인만**(claim 안 함) → UI는 `worker_id` 없는 잡을 '배정 대기'로 표시(`server.py` L2568). 진단 = `CODEX_VIDEO_DESK/TEMP/worker/logs/worker_*.out.log`의 `[setup required] …`. 필요 모듈(`worker.py readiness()` L74)=edge-tts·Pillow·**mutagen**·requests·playwright + remotion·ffmpeg·chromium. 해결=빠진 것만 런타임 venv에 설치 → 워커가 5초 내 자동 claim(패널 재시작 불필요).

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
- `cardnews/_state/content_guide.md` — 사이클 학습 메모 + **발행 토픽 인덱스(§2=중복회피 정본, 자동 생성)**. (2026-06-18 신설)
- `cardnews/scripts/update_content_guide.py` — content_guide §2 자동 재생성. `run_windows.py:267-279` 렌더 성공 후 best-effort 호출(학습 루프 강제). §1·§3·§4·이력 보존.
- `cardnews/scripts/validate_article.py` — 기사 스키마 2단 검증(ERROR=slug·title·cards·captions_md / WARN=content_type·source_line·narration 등) + `--next` 다음 NNN 산출.

**마스터 룰 문서**
- `_docs/INSTRUCTIONS_CARDNEWS.md` — 시스템·수집·발행 마스터.
- `_docs/CARDNEWS_BUILD.md` — 1건 빌드 워크플로 (수집→JSON→prompt.md→이미지→렌더→발행 9단계).
- `_docs/INSIGHTS_LOOP.md` — 시트(유튜브_인사이트 + 메타_인사이트) → 클로드 누적 학습 루프. 시트 직접 Read 단일 모델(코덱스·GitHub·Drive MD·mklink 다 폐기). 매 사이클마다 새로 Read = 시간 갈수록 후보·후킹 정교화.
- `cardnews/templates/caption_template.md` — 5채널 + 영상 나레이션(채널 6, run_pngs 시 captions.md 자동 append) 첫 줄 후킹 분담 표준.

**후보 가중치 라벨 매트릭스 (수집 단계, INSIGHTS_LOOP.md §3 정본)**
- `yt+30%` 유튜브_인사이트 Top 10 키워드 매칭 / `yt-hook+20%` Top 5 후킹 패턴(숫자포함·의문문 등) 적용
- `insta+30%` 인스타 Top 게시물·**릴스**(도달·조회·저장) 주제/포맷 매칭 / `insta+20%` 잘 되는 릴스 포맷 적용 — 소스=`인스타` 시트(Drive 스냅샷 **직접 참조** — 인스타_인사이트 MD 자동화는 **안 만듦**, 사장님 결정. 수집 때마다 사람이 성과 보고 가중치 반영=반복 정밀화로 충분) (★ 2026-06-19 사장님: 콘텐츠 수집은 유튜브+인스타 성과 기준)
- ~~`meta+20%/30%` 메타_인사이트~~ = **콘텐츠 수집에선 제외**(메타_인사이트는 광고 카피용 G단원 전용, 카드뉴스 후보 가중치에 미사용)
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
- 메타_인사이트 시트화 코드 합류(2026-06-18, 정본 G단원): `apps_script/meta-insights-sheet.js`(새 clasp 파일, 기존 85KB meta-sync.js 무수정·전역 스코프로 상수 재사용). 배포 후 1회 `setupMetaInsightsSheetTrigger()`+`writeMetaInsightsSheet()` 실행 → `메타_인사이트` 시트 생성(STEP1 #8 작동). 그 전까지는 메타 가중치 0건.
- **★ 수집 기준일 = KST(한국시간) (2026-06-19).** news D-7 컷오프는 한국시간 기준으로 계산. WebSearch는 미국 기준 결과라 날짜 혼동 주의. **`env`/`currentDate`가 stale일 수 있으니 수집 시작 시 `TZ=Asia/Seoul date`로 오늘 날짜 확인 필수.** `news_d7_filter.py`는 KST(UTC+9, DST 없음) 고정 — `date.today()`는 샌드박스/서버 UTC라 한국 00:00~09:00에 하루 밀림(이 버그로 06-19를 06-18로 오인했음).

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
- `publish_codex_package.py` — 결과 패키지 + 유튜브 메타. **★ 설명란 빈 버그 수정(2026-06-19)**: publish는 `cardnews/output/<slug>/captions.md`(카드뉴스 렌더가 만드는 파일)에서 캡션을 읽는데, **영상-only 슬러그는 그 파일이 없어** YT설명·Reels·TikTok 본문이 전부 빔. → `article_captions(slug)` 추가해 **기사 JSON(`cardnews/articles/<slug>.json`)의 captions_md로 폴백**. 제목·태그는 원래 정상이라 본문만 비던 증상.
  - `clean_title()`: 이모지(`_TITLE_EMOJI`) + 장식 괄호(`_TITLE_DECOR_BRACKETS=【】〔〕「」『』《》〈〉［］｛｝`) 제거, `?! ~ . ( )`는 유지.
  - `strip_youtube_extra_sections()`/`clean_youtube_description()`: 타임스탬프·핵심데이터·출처 제거.
- 기타: `codex_chunk_overrides.py`(청크 수동분할), `codex_clean_latest_prompt.py`, `codex_refresh_workbench.py`, `validate_codex_korean.py`, `verify_video_quality.py`.

**렌더 엔진**
- Remotion: `shorts/` + `shorts/scripts/render_remotion_fast.mjs`(브라우저 자동탐색 `ensureBrowser`+`findLocalChrome`, Playwright chromium/시스템 Chrome 폴백).
- 진입 bat: `run_codex_casual.bat`(CLI 폴백에서 `--concurrency` 제거됨 — "%" 깨짐 방지).
- 트랙 구분: casual/newsroom(카드뉴스 영상) vs `shorts/promo/`(타이포 홍보) vs `shorts/promo_ai/`(실사 AI 광고, Higgsfield).
- 컴포지션 정의: `shorts/src/Root.tsx`(NewsroomShort/CasualShort/Promo-*/**Cover**, 전부 1080×1920).

**SNS 품질 — 후킹·레이아웃·오디오·닫기 (2026-06-13, 021 품질점검발, 재렌더 검증)**
- **오프닝 후킹**: `shorts/src/components/OpeningHook.tsx` — 검정 → **다크 그라데이션 + 움직이는 주황 글로우 + 주황 키커 pill(채널 태그라인) + 빠른 큰 헤드라인**. `Root.tsx` `OPENING_SEC` 1.5→1.1→**2.0**(후킹 읽을 시간 확보).
- **닫기 CTA 디자인 카드**: `shorts/src/components/casual/CasualCta.tsx`(신설) — 일러스트 폐기, 오프닝과 같은 결(다크+주황글로우+키커 "폰스팟 광교점" + "휴대폰 구매할 땐?" + 주황 펀치 + 연락처 박스 kakao/location/litt). `Composition.tsx` casual cta 분기를 `CasualCard type=cta` → **`CasualCta`** 로 교체(데이터=`script.cta`, audioKey=cta). newsroom은 기존 `CtaCard` 유지.
- **아웃트로 +2초**: `Root.tsx` `OUTRO_SEC` 1.2→**3.2**(끝화면 = `ChannelOutro` 로고+구독 더 길게).
- **카드 전환 애니메이션**: `CasualCard.tsx` `cardEnter`(frame 0~7 페이드+슬라이드업)를 비주얼 컨테이너에 적용 → 하드컷 완화(일러스트 포함 전 카드).
- **제목바 중복 제거**: `shorts/src/components/casual/CasualCard.tsx` — `CasualTitleBar`를 **`type==="hook"`일 때만** 렌더(본문 4개 카드 반복 제거 + 비주얼 영역 확대). 맥락은 오프닝+헤더+비주얼/자막으로 충분.
- **자막 세이프영역**: 점검 결과 자막은 화면 **중하단**(아래 ~700px 흰 여백)이라 플랫폼 UI 안 가림 → 변경 안 함(`CasualCaption` height 840, padding-top 128).
- **★ 자막 정밀 싱크 (B, 2026-06-14)**: 자막 청크 타이밍은 `chunkUtil.ts getChunkWindows`가 잡는데, 원래 **모든 청크에 최소 가독시간 바닥(`CAPTION_MIN_READABLE_FRAMES`=0.5초)** 을 깔고 남는 시간만 weights로 분배 → 짧은 청크가 음성보다 길게 잡혀 **미묘한 드리프트**. 수정: 타이밍이 **정밀 모드(`_tts_timing.mode==="word_boundary_text_align"`)면 바닥=0** → 자막이 실제 발화에 정확히 비례(=정확 동기화). 추정(char fallback) 모드만 바닥 유지(가독 보호). 전파: `CasualCard`가 `data._tts_timing.mode` 읽어 `preciseTiming` → `chunkIndexFromList`/`getChunkWindow`/`getVisualWindow`/`CasualCaption`에 `precise` 전달. 잔여 오차=±1프레임(33ms, 30fps 한계). 검증 023 전섹션 정밀. **+ 자막 페이드인(2026-06-14)**: 청크 바뀔 때 `CasualCaption`이 청크 윈도우 시작 기준 `opacity 0.45→1`+`translateY 9→0`(4~5프레임)으로 살짝 떠오름 — 비주얼 `cardEnter`와 결 맞춤(하드 스위치 완화). 카드 간 크로스디졸브는 **각 카드가 자체 TTS 오디오를 가져 오버랩 시 음성 겹침** → 비채택(cardEnter로 대체).
- **★ 자막 강조 = 작성자 구절만 (2026-06-14, `CasualCaption.tsx`)**: 자동 숫자/단위 강조(`AUTO_EMPHASIS_PATTERNS`)는 과다·번짐으로 **OFF**, `caption_emphasis`(카드당 1구절)만 **브랜드 오렌지(#F74B0B)**. 매칭=토큰 사이 공백/줄바꿈만 허용하는 정확 정규식(`escapeRegExp`+`\s*`), **못 맞으면 스킵(색 X)**=「애매하면 안 칠한다」. 검증 022 "5분" 오렌지.
- **라우드니스 −14 LUFS**: `shorts/scripts/finalize_sns_video.py` `common_prefix`에 `-af loudnorm=I=-14:TP=-1.5:LRA=11`(나레이션 −16.5가 작던 문제). env `PHONESPOT_TARGET_LUFS`(기본 -14, `off`로 끔).
- **BGM / 오프닝 스팅 (2026-06-16)**: 전체 BGM은 여전히 보류(나레이션 무음구간 多). **단 오프닝 후킹 썰렁함 해소용 스팅 추가** — `Composition.tsx` 루트(`<AbsoluteFill>` 바로 안, 오프닝 Sequence **밖** = 0초부터)에 casual 한정 `{isCasual && <Audio src={staticFile("music/opening_sting.mp3")} volume={0.7} />}`. 에셋 `shorts/public/music/opening_sting.mp3` = **3.0초·페이드인 없음·2~3초 페이드아웃**(2초에 후킹 나레이션 시작 → 페이드꼬리가 그 위로 빠짐). 오프닝 2초 고정(`Root.tsx OPENING_SEC=2.0`)이라 매 영상 동일 동작 = 음원 충돌 없음. ffmpeg 재생성 = `-t 3.0 -af "afade=t=out:st=2:d=1"`. **함정: `*.mp3`는 `.gitignore`(line 91)라 git 비전파 → 렌더하는 PC `shorts/public/music/`에 직접 둬야 함**(기존 calm_01 등과 동일). 코드(`Composition.tsx`)는 git 전파. 번들은 public/src 해시 감지로 자동 재빌드(패널 재시작 불필요). **+ CTA 스팅 (2026-06-16, 검토대기)**: 닫기("휴대폰 구매할 땐?") `<Sequence from={ctaStart} durationInFrames={Math.ceil(5*fps)}>` 안에 `<Audio src={staticFile("music/cta_sting.mp3")} volume={0.6} />`(casual 한정, `Composition.tsx:82-87`). 에셋 `shorts/public/music/cta_sting.mp3` = **5.0초·페이드인 없음·4~5초 페이드아웃**. CTA 나레이션 위로 깔려 볼륨 0.6(오프닝 0.7보다 낮음). 현재 두 스팅 모두 트랙 앞부분 사용(오프닝 0~3초·CTA 0~5초 = 첫 3초 동일, 북엔드). `ctaStart`부터 5초가 CTA+아웃트로 길이 안에 들어감(outro 3.2초). ffmpeg = `-t 5.0 -af "afade=t=out:st=4:d=1"`.
- **길이 목표**: 35~45초(56초는 길다). 레버는 코드가 아니라 **기사 집필**(J단원 `article_authoring_spec.md`: 카드 본문 문장 ≤35자·6카드 ≈250자).
- **★ UI 슬림 + 경쟁채널 벤치마크 (2026-06-19, 종민).** `CasualHeader.tsx` height **116→88**(헤더는 매 카드 baked-in 주황 '폰스팟 IT' 바 → 비주얼 세로 +28px). 실제 영상(028, 59.4초) 프레임 분석 결론: ① 오프닝 헤드라인은 **이미 상단/중앙 큼직**(OpeningHook, 싸당과 동일 구조) = 위치 문제 아님, **후킹 '문구'가 설명형**이라 약함 ② 비주얼 컨테이너는 **이미 풀폭**(flex:1) — raster는 `ImageVisual` **objectFit:contain**(여백=의도, 뒤 블러본이 채움)·SVG일러스트 여백=**아트워크 자체** → '좌우 여백 줄이기'는 단순 CSS 아님(cover=가장자리 잘림 위험/아트 재제작/헤더슬림이 레버) ③ **진짜 퀄 문제는 사이즈가 아니라 약한 그림**(generic 금지아이콘 등 = lexical-fallback 매칭, CLIP 꺼짐). **조회수 우선순위(벤치마크)**: 길이(25~35초) > 후킹 문구(애플/삼성 루머+손해회피, 싸당식) > 비주얼 매칭 품질(CLIP) > UI 배치(거의 OK, 최하). 싸당 히트(14만·13만)=아이폰 루머+손해회피 훅. 노출 거의 0 = 콜드스타트/분포 문제 = 브레이크아웃 1방 필요(평타 누적 X). 진단 정본=유튜브_인사이트 시트(노출·CTR·유지율).
- **수정 시 읽을 것(SNS품질)**: `OpeningHook.tsx`(후킹) / `CasualCard.tsx`(레이아웃) / `finalize_sns_video.py`(오디오/인코딩). 함정: TSX는 샌드박스 렌더 불가 → esbuild 구문검증 + **실행PC 재렌더로 시각 확인** 필수.

**커버(표지) 9:16 정지컷 — 영상과 같이 생성 (2026-06-13 신설)**
- 컴포넌트: `shorts/src/Cover.tsx`(`CoverShort`). 정적 1프레임. hook 헤드라인(`headline_lines`, 없으면 `video_title` 분할) + 매칭 일러스트(hook→facts의 첫 `illust`/`image` → `background_image` 폴백) + 폰스팟 브랜딩.
  - 일러스트 경로 규칙: `illust`→`assets/illustrations/<value>.png`, `image`→`assets/<value>`.
- 컴포지션 등록: `Root.tsx` `id="Cover"`(durationInFrames=1).
- 렌더 스크립트: `shorts/scripts/render_cover.mjs`(`renderStill`, `render_remotion_fast.mjs`와 **같은 번들 캐시 재사용** → src 미변경이면 재번들 X). 인자 `<outPath> [compId=Cover]`. `.jpg`면 jpeg(q92), 아니면 png.
- 파이프라인 배선: `run_codex_casual.bat` Step 6(finalize) 직후 **best-effort** 단계 → `RESULTDIR\<RESULTKEY>_cover.jpg` 생성(실패해도 영상 빌드 안 막음, `[WARN]`).
- 데이터 출처: `shorts/public/shorts_script.json`(semantic match 끝난 effective 스크립트) — 영상과 동일. 그래서 커버 렌더는 영상 렌더 뒤에 둠(매칭된 실제 일러스트 반영).

**수정 시 읽을 것 (커버)**: `Cover.tsx`(레이아웃/헤드라인/비주얼 선택) + `render_cover.mjs`(출력 포맷) + `run_codex_casual.bat` 커버 블록. 버전 4.0.404 기준 `renderStill` 파라미터 = output/frame/imageFormat/jpegQuality.
**함정(커버)**: src 첫 변경 후 첫 렌더는 1회 재번들(이후 캐시). 헤드라인 폴백까지 비면 빈 텍스트 → `video_title` 필수.

**promo 타이포 트랙 + 자가개선 루프 (2026-06-18 신설/확장)**
- 정본 3종: `shorts/promo/README.md`(트랙 정본) · `HOOK_LEARNING.md`(학습 루프) · **`AUTOLOOP_DESIGN.md`(200~300편 데이터기반 자가개선 설계, 미구현 로드맵)**. promo는 casual/newsroom과 별엔진 = `src/components/promo/` + `scripts/promo_*.py` + `run_promo*.bat`. **나레이션 없음(효과음+음악만)** — `PromoShort.tsx`는 sfx(:68)+music(:76)만 재생, `tts`/`나레이션` 필드는 **비렌더 카피 메모**(GUIDE_TYPOGRAPHY 정정 박음).
- **편집=MD 권위**: `promo/review/NNN_*.md` → 렌더 직전 `promo_md2json.py`(이제 `__main__` 가드 = import 시 `build()`만, 파일 안 씀) → JSON. 정합검사 = `promo_check_sync.py`(read-only, 드리프트 시 exit 1).
- **학습 신호**: review MD 머리 `- 후킹: <8종>`(질문형·단언형·비교형·한정형·가격강조·감성·공감·위협형·FOMO형). 12편 채움(질문5·단언3·비교1·한정1·감성1·FOMO1, **초안 분류=조정가능**). `promo_manifest.py`가 렌더마다 1행 + `variant_id`(slug+preset+styles+music 해시, 옛 행 자동 백필).
- **성과 귀속 = 관리시트 운영일지(2026-06-18 결정)**: 성과 출처 = 관리대장 `유튜브`/`인스타` 운영일지의 **조회수·좋아요(수기)**. 새 API·OAuth·업로드로그 불필요. 업로드=사람, **운영일지 비고에 promo `outfile` 기재 = 유일 조인키**. ingestion = Claude가 Drive 스냅샷 읽어 `promo/_results.csv`(컬럼 pull_date·platform·outfile·slug·preset·url·views·likes) 떨굼(폴백 수동 = `promo_results_add.py`). 집계 = `promo_score.py`(outfile로 manifest 조인 → 후킹/프리셋/스타일 **축 풀링** + 게이트 `--gate` 기본 5000 + 랭킹). 생성 근거 패널 = `promo_plan.py`(읽기전용: 작성후킹분포·렌더분포·후킹성과·미커버셀).
- **수정 시 읽을 것**: 위 정본 3개. 성과/생성 로직 = `promo_score.py`·`promo_plan.py`·`promo_manifest.py`.
- **함정**: ① **이 폴더=구글드라이브 스트리밍 → bash 마운트가 일부 파일을 잘린/낡은 캐시로 read**(2026-06-18 `promo_manifest.py`에서 재현: cp가 line44에서 truncate). 검증은 **file-tool(Read) 또는 PC**에서. 편집 자체는 정상 반영됨. ② 성과 데이터 0건이면 score/plan의 **성과 가중=0**(노이즈 회피, 설계서 §5/§9) — 개별 영상은 노출 작아 비교 불가, **축 풀링 필수**. ③ 인사이트 시트(`유튜브_인사이트`) Top 후킹 패턴 아직 미산출(GEMINI 키 필요) = 인사이트 가중도 현재 얕음. ④ 음악: 무드당 곡 채워야 로테이션(`promo_pick_music.py` fallback은 sting/규칙위반 제외 후 정상무드만, 없으면 off) — 음원 수급=종민.

**마스터 룰 문서**
- `_docs/INSTRUCTIONS_SHORTS.md`(주의: 옛 MoviePy/Typecast 설계 잔존, 현행 Remotion과 일부 불일치).
- `CODEX_VIDEO_DESK/README.txt`, `CODEX_VIDEO_DESK/MAINTENANCE/CODEX_MASTER_VIDEO_GUIDE.md`.

**수정 시 읽을 것**
- 스크립트 생성 로직: `build_script.py`만.
- 자막 타이밍/동기: `codex_caption_lockstep.py` + `codex_enhance_script.py`.
- **★ TTS 타이밍 graceful fallback (2026-06-14)**: `generate_tts.py build_chunk_timing`이 단어경계 정렬 실패 시(날짜 "7월 22일"·영문 "Z 폴드8" 등 **TTS 발음≠글자**) RuntimeError로 **빌드를 죽이던 것 → `character_weight_fallback` 반환**(근사 동기화로 렌더). `verify_tts_timing.py`: ① `mode != word_boundary` 무조건 에러였던 것 → char_fallback은 통과(unexpected 모드만 에러) ② **ms/window 검사를 word_boundary 모드에서만** 실행(char_fallback은 weights=글자수·windows=[] 라 ms로 보면 "22ms 너무짧음" 오탐). `run_codex_casual.bat`: `verify_tts_timing.py --allow-char-fallback`(char_fallback→경고). **결과: 날짜/영문 섹션만 근사싱크+경고, 나머지 정밀, 빌드 성공.** 그 섹션도 정밀 원하면 기사 한글화(날짜·영문 풀어쓰기) 또는 `pip install -U edge-tts`. 검증 024 hook.
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
  - **매칭 경로**(`semantic_match` 청크 루프): ① 실사 포토(렉시컬 모델명) ② 소스 카드이미지 ③ **일러스트 렉시컬 키워드**(아래 ★) ④ 라이브러리 일러스트 텍스트/태그 임베딩(`best_ill ≥ EMBED_MIN_ILLUST`) ⑤ 소스(photos/ 제외)/마스코트 유지 ⑥ 그림내용(CLIP) ⑦ 중립 필러(`pick_neutral`). 엔진 없으면 lexical 임계(`MIN_*_SCORE`).
  - **★ 일러스트 렉시컬 키워드 매칭 (2026-06-14, 임베딩 보조)**: 한글 임베딩이 해시 이름(`mid_release_98cab19a`)+헤드라인 문맥에 희석돼, DB keywords가 청크와 정확히 겹쳐도 코사인이 임계를 못 넘던 불안정 해결(포토를 렉시컬로 고친 것과 같은 처방). `build_illust_keyword_index`(available+키워드 보유, cpt/blocklist 제외) + `illust_lexical_hits(keywords,chunk)`(한글=부분문자열·영문/숫자=단어경계, `ILLUST_KW_STOP` 흔한단어 제외) → `best_lex_ill`. chosen에서 **`hits ≥ MIN_ILLUST_KEYWORDS`(env, 기본 2)면 임베딩 best_ill보다 우선**. 청크 자체 기준(헤드라인 제외). 약한 청크(h<2)는 임베딩 유지 = 무회귀. 검증(021): mid_release/official_sale/mounted_body가 키워드대로 제자리, smartphone 반복 6→4. 로그 `[illust-kw] <sec> c<i>: <variant> hits=N`. **★ content-gate 면제 (2026-06-14)**: 키워드 ≥2 매칭(cpt 제외)은 **CLIP content-gate를 건너뛴다** — '범용/추상'으로 그린 일러스트를 CLIP이 거부해도, 키워드가 청크에 실제로 박혀 있으면 그게 더 신뢰할 신호. content-gate는 약한 임베딩 픽(best_ill)에만 적용(이름↔그림 불일치는 거기서 계속 차단). 검증 022: personal_data(2히트)·lock_screen_only(4히트) 복귀.
  - **상수(전부 env 오버라이드)**: `EMBED_MIN_IMAGE`(0.42)·`EMBED_MIN_ILLUST`(**0.48**, 0.42는 너무 관대해 먼 그림 통과)·`EMBED_MIN_ILLUST_IMG`(0.28, CLIP 내용)·`NEUTRAL_FILLERS`(★ 진짜 중립 phone/device만 — newspaper/shield/microphone/meeting_room/forecast는 "특정 의미"라 제외)·`ILLUST_BLOCKLIST`(기본 비움, env 비상용)·`EXCLUDE_UNVERIFIED_CONCEPT`(기본 True).
  - **★ 범용 오배치 방지 3종 (2026-06-13, SNS 품질점검 후)**:
    1. **중립 폴백 정상화**: 매칭 실패 시 의미 있는 그림(방패/신문/마이크) 대신 phone/device 일반 그림.
    2. **content-gate(CLIP)**: 텍스트로 고른 일러스트도 실제 그림이 주제와 맞는지 `EMBED_MIN_ILLUST_IMG`로 검증. **단 CLIP 그림엔진(`codex_image_embed`/`image_embed_cache.json`)이 설치돼야 작동** — 없으면 무력(빈 데이터→통과).
    3. **미검증 개념아트 정책(`_is_unverified_concept`)**: `cpt_*`(개념요청 텍스트로 자동생성, 그림 미검증)는 **텍스트매칭에서 제외**(CLIP 켜지면 content 경로로만 검증 사용). 이름 하드코딩 대신 카테고리 규칙 — cpt_496029c6(=AI개념인데 보이스피싱 그림) 같은 케이스 일괄 차단. 읽기이름 일러스트는 영향 없음.
  - **★ 실사 포토 라이브러리 (2026-06-13, 사장님 설계)**: 일러스트와 별개 폴더 `shorts/public/assets/photos/`. 사장님이 '사용 권리 확보된' 실사를 **한글 파일명(=라벨)**으로 넣음(예 `삼성_엑시노스.JPG`, `갤럭시z플립7_z폴드7.JPG`, 언더스코어=공백). 매칭 우선순위 = **① 포토(모델명 일치) → ② 일러스트(기존) → ③ 일러스트 생성요청**.
    - **★★ 매칭 방식 = 임베딩 아님, 렉시컬 모델명 일치 (2026-06-14 전환).** 한글 임베딩(MiniLM)이 모델명(갤럭시A vs 엑시노스 vs S25)을 못 구분 → 임베딩 코사인으론 엉뚱한 폰이 매칭됨(렌더 증거: 플립 청크에 갤럭시A, 엑시노스 청크에 S25, 통신사 로고 곳곳). **임계값은 "정답>오답 간격"이 있을 때만 작동하는데, 여기선 정답·오답이 다 ~0.5에 겹쳐 어떤 PHOTO_MIN으로도 못 가름** → 신호 자체를 렉시컬로 교체.
    - **렉시컬 규칙**: 파일명을 토큰화(`_photo_tokens`: 공백/_/- + 한글|영문|숫자 경계) → 그 토큰이 **청크 텍스트에 실제 등장**할 때만 채택. **구별 토큰**(`_is_distinctive`: 한글≥2·영문≥3·숫자≥3, `PHOTO_STOP` 제외)이 ≥1개여야 함. `photo_lexical_score(label,chunk)→(구별수,일반수)`. 동점이면 일반토큰 일치수로. `best_photo=(dist,gen,file)`, chosen **0순위 = dist≥1**.
    - **`PHOTO_STOP`**(env `PHONESPOT_PHOTO_STOP`): 삼성/갤럭시/애플/퀄컴/로고/폰/스마트폰 등 일반 토큰 — **이것만으론 채택 X**. 그래서 `삼성_갤럭시A`·`S25`가 무관 청크(예 플립영상)에 안 붙음 = 커버 오염의 근본 차단. `엑시노스`/`스냅드래곤`/`플립`/`폴드`/`배터리`/`아이폰`은 구별 토큰 → 그 단어 있는 청크에만.
    - **결과(021 검증)**: 엑시노스→엑시노스칩청크, 플립→플립청크, 배터리→배터리청크 정확. `갤럭시A`·`S25`·통신사로고는 해당 단어 없는 영상에서 자동 제외.
    - **★ 임베딩 완전 불필요 → 모델 미설치 PC(부사수)에서도 작동.** `build_photo_index()`/`PHOTO_MIN`은 더 이상 매칭에 안 씀(상수는 잔존, 무해). bat의 `PHONESPOT_PHOTO_MIN`도 미사용. 한 사진은 used_visuals로 **한 청크에만**(중복 사용 시 다음 청크는 일러스트 폴백).
    - 선택 시 `{"type":"image","value":"photos/<file>"}` → 기존 `ImageVisual`이 `staticFile('assets/photos/<file>')` 켄번스 모션으로 렌더(렌더러 변경 X). 진단 로그 `[photo] <sec> c<i>: <file> dist=.. gen=..`.
    - 폴더 README(명명·예시·저작권 주의) + `.gitignore` 등록(실사=대용량/저작권, **git 비추적 → 렌더하는 PC에 직접 있어야 함**, Drive/로컬 공유).
- `codex_illust_embed.py`(텍스트 임베딩 `ce`, fastembed `paraphrase-multilingual-MiniLM-L12-v2`) / `codex_image_embed.py`(이미지 CLIP `ie`, jina-clip-v1).
- `codex_illust_match_preview.py` — 읽기전용 의미매칭 미리보기.
- `codex_concept_scout.py` — **개념 발굴형 스카우트**: 라이브러리에 없는 갭을 범용 개념으로 발굴.
  - `readable_variant()`: Gemini 번역으로 `<english_slug>_<hash8>` 사람읽기 이름. 키 없으면 `cpt_<hash8>` 폴백.
  - 캐시 `shorts/config/concept_name_cache.json`(git 비추적). 키파일 `_secrets/gemini_key.txt`.
- `codex_illustration_scout.py`(필수 일러 요청, 13 고정규칙 RULES, `MAX_REQUESTS` = **5**[2026-06-14, 3→5]) / `codex_illustration_db.py` / `codex_unique_illustration_guard.py` / `codex_warm_embeddings.py`. ※ 서브(자동발굴)=`codex_concept_scout.py` `MAX_NEW_CONCEPTS`=5. 패널 "신규 일러스트 요청서" = 필수 5 + 서브 5. 생성단계에서 많이 채울수록 렌더 매칭 품질↑(graceful degradation: 채운 만큼 고퀄, 못 채우면 렉시컬로 최선).
  - **★ `codex_unique_illustration_guard.py` 버그 수정(2026-06-13)**: 이 가드는 semantic_match **다음에** 돌며 "중복 일러스트를 유니크하게" 바꾸는데, **매처의 제외 규칙(cpt·blocklist)을 무시**하고 반복된 중립 필러까지 강제 교체해 **매처가 걸러낸 cpt_496029c6(사기그림)·무관 그림을 되살렸다**(매칭 망가짐의 진짜 뿌리). 수정: `_is_bad_variant`(cpt·blocklist 제외) + **중립 필러(`_NEUTRALS`)는 반복 허용**(억지 유니크 금지). 매처와 같은 env(`PHONESPOT_ILLUST_BLOCKLIST`/`_TRUST_CONCEPT_ART`/`_NEUTRAL_FILLERS`) 사용. **교훈: semantic_match 뒤에 비주얼을 만지는 모든 단계(guard·scout·apply)는 같은 제외 규칙을 따라야 한다.**
- 지문/사용이력: `shorts/codex/ILLUSTRATION_TAG_DB.md`, `shorts/codex/illustration_usage_history.json`(런타임, git 비추적).
- **★ 수동 라이브러리 등록 (2026-06-16)**: 임의 일러스트를 ILLUSTRATION_DROP에 떨구는 것만으론 **매칭 안 됨**. 매처는 폴더 스캔이 아니라 **DB(`illustration_tag_db.json`) 순회**(`codex_semantic_visual_match.py:303` `for variant,entry in db["illustrations"]`; `:304` variant가 `library_variants()`(=`shorts/public/assets/illustrations/*.png` 실파일)에 있을 때만 후보). 즉 **DB 엔트리의 keywords가 매칭 신호, 파일명은 DB↔파일 연결 키일 뿐.** sync(`sync_codex_illustrations.py`)는 복사만, apply(`codex_apply_uploaded_illustrations.py:51`)는 요청서(`codex_illustration_requests.json`)의 variant만 처리(임의 파일 자동등록 X). **수동 등록 절차**: ① `illustration_tag_db.json`의 `illustrations`에 `{<variant>:{tags,keywords,note,available:true}}` 추가(원자적 write=temp+os.replace) ② `<variant>.png`를 `shorts/public/assets/illustrations/`에 둠. **둘 다 git 추적 → 전파됨**(포토/음악과 달리 일러스트는 git 전파). 렌더 시 청크 텍스트에 keywords ≥2 뜨면 렉시컬 채택, 약하면 임베딩 보조. **함정: available:true여도 png 없으면 `:304`가 스킵(크래시 X, 안 쓰임).** 2026-06-16 등록 4개: `camera_quality`/`document_article`/`fast_charging`/`battery_capacity`(사장님 제작 3D 실사풍). ※ **그림에 텍스트가 박힌 일러스트**(예 camera_quality "카메라 성능 더욱 선명하게")는 keywords를 좁혀 그 주제에만 뜨게 할 것 — 범용 사용 시 박힌 문구가 무관 기사에 안 맞음(범용성 원칙 위배 방지).

**수정 시 읽을 것**
- 매칭 알고리즘: `codex_semantic_visual_match.py` (+ embed 모듈).
- 개념 발굴/이름: `codex_concept_scout.py`.

**함정**
- 임베딩 모델 ~1GB. 설치/워밍은 `SETUP_FULL_PRODUCER.bat` / `codex_warm_embeddings.py`.
- Gemini 키 없으면 readable 이름 폴백(cpt_) — 에러 아님. **단 cpt_는 그림 미검증이라 텍스트매칭 제외(위 정책 3)**.
- **★ CLIP 그림엔진(`codex_image_embed`)이 PC에 미설치면 content-gate 무력** → 텍스트/태그 매칭만으로 동작. 즉 "이름↔그림 불일치"의 범용 차단은 **CLIP 켜야 완전**. 안 켜진 동안은 정책 3(cpt_ 제외)+중립폴백+임계 0.48이 방어선. 검증 단서: `shorts/codex/image_embed_cache.json` 존재 여부.
- **★ 모델 로드 무한대기 → 패널 `Failed to fetch` (2026-06-18 실증·수정).** 모델 캐시 없는 PC(로컬)에서 첫 `ImageEmbedding(jina-clip)` 생성이 네트워크 다운로드를 시도하다 멈추면 try/except는 *예외*만 잡고 *행*은 못 잡아 `available()`→`codex_import_propose.py`→server.py `subprocess.run`(timeout 無)이 전부 무한대기 → 브라우저 fetch 실패. **수정**: `codex_image_embed._call_with_timeout`(모델생성 스레드 타임아웃 `PHONESPOT_CLIP_LOAD_TIMEOUT`=25s; 초과시 None=unavailable→스크립트가 fallback-mtime 제안 생성) + `HF_HUB_DOWNLOAD_TIMEOUT=15`/`HF_HUB_ETAG_TIMEOUT=10` + (A단원 백스톱) server.py `video_import_propose`/`card_import_propose`의 `subprocess.run(timeout=120)`+`TimeoutExpired` 처리. 캐시된 부사수 PC는 수초 로드라 무영향. **CLIP 진짜 매칭은 모델 있을 때만**(없으면 시간순 폴백 제안=패널서 수동보정).
- **★ CLIP 설치/워밍 (2026-06-14 완료)**: `fastembed`의 `jinaai/jina-clip-v1`(이미지+텍스트 768차원). 설치=`pip install fastembed numpy pillow onnxruntime`. **함정: ImageEmbedding만 받으면 텍스트 모델(`onnx/text_model.onnx`)이 안 받아져 `available()=False`** → `huggingface_hub.snapshot_download('jinaai/jina-clip-v1', cache_dir=<TEMP>/fastembed_cache)`로 저장소 전체 받아 채움. 워밍=`codex_warm_embeddings.py`(라이브러리 지문 → `image_embed_cache.json`). **캐시가 `%TEMP%\fastembed_cache`(휘발)** → 청소도구에 지워지면 content-gate 조용히 OFF(에러 없이 텍스트 폴백). 임계 `EMBED_MIN_ILLUST_IMG`=교차모달이라 0.2~0.32가 정상(0.6 걸면 전멸). **0.28 너무 엄격 → bat env `PHONESPOT_IMG_MATCH_MIN=0.24`**(run_codex_casual.bat). 단 022처럼 영문/추상 기사는 0.24도 다 거부(콘텐츠 한계, 임계 아님 → 기사 한글화가 레버).
- **잘못 그려진 정식(비-cpt_) 일러스트**(예: ti_decrease=티타늄'감소'를 슬림화에 사용)는 특정 이름 하드코딩 ❌(원칙). 해결=그 그림을 더 중립/정확한 것으로 교체하거나 CLIP content-gate 활성화.
- **실사 포토가 안 뜸**: ① 사진이 **렌더하는 PC에 없음**(git 비추적 → 노트북에 넣고 사무실 렌더면 누락) ② **모델명이 청크에 안 나옴**(렉시컬 = 단어 실제 등장 필요. 예 "갤럭시 A" 영상인데 청크가 "A"만 쓰면 너무 짧아 미채택 — 이게 정상, 무관 청크 오염 방지의 대가) ③ 파일명이 일반 토큰뿐(삼성·갤럭시·로고)이라 `PHOTO_STOP`에 걸림 → **구별되는 모델명/키워드를 파일명에 넣어야**(예 `삼성_갤럭시A` X → `갤럭시A33_보급형` 처럼 구별 토큰 추가) ④ 새 코드 미전파(push→pull). 로그 `[photo] <sec> c<i>: <file> dist/gen` + `photos=N장(렉시컬 모델명 매칭)`로 확인.
- **약한/그리디 매칭(appliance·ti_decrease 류)**: 매처가 0.48 턱걸이로 약한 일러스트를 고르거나(예 "엑시노스"에 appliance), 적합 일러스트가 1개뿐일 때 **앞 청크에서 소진**돼 정작 핵심 청크가 차선을 받음(그리디 per-chunk). 범용 해결 = ① 그 주제 **사진/일러스트 보강**(photo가 0.48을 이기면 대체) ② CLIP content-gate 활성화 ③ `EMBED_MIN_ILLUST` 상향(약한 건 중립으로, 단 중립 반복↑). **특정 이름 하드코딩 ❌.**
- **★ 태그 DB(`shorts/config/illustration_tag_db.json`) 손상 = 일러스트 불안정의 숨은 원인 (2026-06-14)**: `write_json`이 비원자적(`write_text` 직접)이라 렌더 중 쓰기가 끊기면(크래시·동시실행) DB가 truncate/NUL 손상 → `read_json`이 파싱 실패 시 **빈 DB 반환** → 매처가 라이브러리 통째로 잃고 중립으로 추락(키워드 매칭 0). **수정: `codex_illustration_db.py` `write_json` 원자적(temp+`os.replace`)** → 손상 차단. 손상 시 복구 = `git show HEAD:shorts/config/illustration_tag_db.json`(또는 plain `cp`, **`git checkout`은 .gitattributes 필터가 NUL 유발 가능 — 우회**). ※ DB는 load_db가 매 실행 filesystem(`library_variants`)에서 재구성하므로 구조는 self-heal하지만 **rich 키워드는 잃음**(auto/library만) → 손상 후엔 검수 일러 키워드 재등록 필요.
- **★ stale 포토가 keep-source로 되살아남 (2026-06-14 수정)**: `build_script`는 기존 shorts_script.json을 **보존**(수동 다듬기 유지). 그래서 임베딩 시절 박힌 낡은 `photos/` 값이 chunk_visuals에 남고, 매처의 "kept source image" 분기가 그걸 되살림(매처가 dist=0으로 거부해도). 수정: keep-source 분기에서 **`photos/` 제외** → 포토는 렉시컬 매처만 (재)배정. 원칙: semantic_match 뒤·INPUT의 photos/는 매처가 매 렌더 재판정.
- **★★ Edit 도구가 큰 파일(>~26-31KB) 꼬리를 통째 truncate (2026-06-14 실사고, 매처 main 소실).** 이 파일이 커지자 **Edit 도구·Read·cat·grep·git show가 모두 ~31KB 지점에서 캡**(예: `return boo`에서 끊겨 보임). Edit 도구가 그 캡된 버전을 읽어 되쓰면 **호스트 파일의 main()/__main__이 통째로 날아감** → `python ...match.py`가 아무것도 안 하고 exit 0 → 매처 죽음(사진·매칭 0, 에러 없음). 깨진 버전이 자동커밋으로 git에까지 올라감. **규칙: 이 파일(및 server.py 등 대형)은 Edit 도구 금지, bash-python(open/write, 캡 없음)으로만 수정.** 진실 확인도 Read 말고 `python -c "print('def main' in open(...).read())"`. **복구법: `git log -- <path>` → 각 커밋 블롭을 `git show <c>:<path> > /tmp/x; grep -c "def main" /tmp/x`로 main 있는 최신 커밋 찾기 → 본문은 현재(내 수정 포함) + 꼬리는 그 커밋, 공통 앵커로 splice(`cur[:i]+good[j:]`).** 6144576에서 복구함.
- **pick_neutral 로테이션 (2026-06-14)**: 중립 5종을 다 쓰면 항상 첫째(smartphone) 반환 → 영문/설정 청크 많은 기사서 smartphone 11회 쏠림. `_NEUTRAL_RR` 라운드로빈으로 분산(검증 214114: 5종×3 균등). `write_json`도 원자적(temp+os.replace)으로 바꿈(매처 출력 shorts_script.json NUL/truncate 방지).
- **수정 작업법**: 이 파일은 Edit 누적이 꼬리를 truncate한 적 있음(2026-06-13) → 큰 변경은 **bash-python(assert count==1 + py_compile + tail 확인)**, 깨지면 `git show HEAD:<path>`의 꼬리로 복구. ※ **bash 마운트는 호스트와 어긋날 수 있음**(마운트 py_compile 오류·grep NUL이 호스트엔 없을 수 있음) → 호스트 진실은 **Read 도구**로 확인. 렌더는 호스트 파일을 읽음.

---

## F. Git & 멀티PC 역할 & 리포 위생  ★ 2026-06-15 머신 모델 갱신 (CLAUDE.md STEP 0 정본)

**머신 역할 (CLAUDE.md STEP 0이 최우선, 2026-06-15 갱신)**
- **로컬 PC**(사무실, `C:\backup\phonespot_cardnews`) = **개발+편집+운영 단일 작업 머신**. 모든 task(광고운영·카드뉴스·영상·기사·.bat) 여기서 수정 → commit → push. **push only**.
- **노트북** = 크롬 원격 입구만(사무실 못 갈 때 로컬 PC 조종). **직접 작업·git 수정 ❌**.
- **부사수 PC**(`C:\PhoneSpot\phonespot_cardnews`) = 카드뉴스·영상·패널 렌더링 전용 단독 생산기. **pull only**.
- **메인 PC**(192.168.0.7) = 카드 이미지 원본 자산.
- 원칙: 로컬 PC 수정 → push → 부사수 PC pull → 부사수 PC에서 실행(렌더링만). 광고운영은 부사수 거치지 않음(Google 클라우드). **push는 로컬 PC에서만**(다중 writer 분기 방지).
- **광고운영 트랙 자동 배포(Phase 1, 2026-06-11)**: 로컬 PC `apps_script/` 수정 → git push → GitHub Actions가 `clasp push --force` → Apps Script 콘솔 자동 반영. **콘솔 직접 수정 ❌**(force push로 덮어쓰임).
- ※ 옛 모델("노트북=push only", 2026-06-08~14) 폐기. 옛 가이드 `_docs/DEV_LAPTOP_OFFICE_RUN_GITHUB.md`의 사무실 push 모델도 폐기 상태 유지.

**git 실행파일 탐색**
- **로컬 PC**: Git for Windows 2.54.0 설치 완료(2026-06-11 Phase 1 셋업 시). PATH에 잡힘 → `git` 직접 호출 OK.
- 이 환경엔 Git for Windows가 **설치 안 됨**(옛 사실 = 노트북 시점 기록 = 다른 머신에서 셋업 시 참고용). git은 **GitHub Desktop 내장본**만 존재:
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
- `CODEX_VIDEO_DESK/런타임파일_git정리_1회.bat` — **런타임 생성물 git 추적 해제(1회, 메인/로컬 PC)**. `git rm --cached` 후 commit → `pull --no-rebase --no-edit` → push.
- `CODEX_VIDEO_DESK/기사_깃에_올리기.bat` — articles+.gitignore push(pull→push).
- `노트북_깃허브_올리기.bat`(리포 루트) — **파일명은 옛 모델 잔재**. 실제 용도 = **로컬 PC 전용** `git add -A`+commit+push(=push 머신용).
- `CODEX_VIDEO_DESK/부사수PC_원클릭_셋업.bat` — 빈 PC 1파일: winget git/node/python → clone(stash 후 pull) → `SETUP_FULL_PRODUCER` → Drive Y/N. UNC 경로 가드.

**자동 업데이트 (수신PC 옵트인)**
- 마커: `CODEX_VIDEO_DESK/TEMP/panel/auto_update.on`.
- 켜기/끄기: `수신PC_자동업데이트_켜기.bat`/`끄기.bat`(구호환 `2번째PC_자동업데이트_켜기.bat`).
- 패널 기동 시 `dashboard/auto_update.cmd`가 `git stash --include-untracked` → `git pull --ff-only`(항상 exit 0, 패널 안 막음).

**런타임 파일 git 비추적 (★ "가만히 있어도 M 뜨는" 원인 차단)**
- 패널/렌더/동기화가 계속 재생성하는 git 추적 파일이 가짜 M·pull충돌의 뿌리.
- `.gitignore`에 추가(이미 반영): `shorts/config/illustration_tag_db.json`, `shorts/codex/ILLUSTRATION_TAG_DB.md`, `shorts/codex/illustration_usage_history.json`, `shorts/public/shorts_script.json`, `shorts/public/assets/illustrations/`, `shorts/config/library_share_path.txt`, `shorts/config/concept_name_cache.json`. **un-ignore**: `cardnews/articles/`.
- 적용 = `런타임파일_git정리_1회.bat` 1회 실행(메인/로컬 PC). 이후 그 파일들 재생성돼도 git이 안 잡음.

**git 전파 vs 비전파**
- 전파(코드 허브): 코드·`.bat/.ps1/.mjs`·`cardnews/articles/*.json`·가이드·`.gitattributes`.
- 비전파(Drive/LAN/셋업으로 따로): `cardnews/images`·`output`·`_secrets`·`node_modules`·임베딩·런타임 생성물·`library_share_path.txt`.

**GitHub 연동 스크립트 (`MAINTENANCE/`)**
- `codex_github_upload.py`(add→commit→pull→push, 로그 `TEMP/github_upload.log`), `codex_github_update.py`(의존성), `codex_github_status.py`. 셋 다 `find_git()` 보유.

**수정 시 읽을 것**
- 새 git bat 만들 때: **이 단원의 GIT 패턴만** 복붙 + I 단원 인코딩 규칙.
- push 실패: `TEMP/github_upload.log` + 머신 역할(로컬 PC만 push).

**함정**
- (옛 사실, 노트북 시점) 노트북엔 Git for Windows가 없음 → "git not found"는 보통 **bat 탐색 코드 문제**지 미설치가 아님. 먼저 GitHub Desktop 경로 확인. **★ 새 모델(2026-06-15)**: 로컬 PC에는 Git for Windows 2.54.0 설치 완료 → `git` PATH 호출 정상. 옛 함정은 노트북/메인 PC 등 다른 머신에서만 해당.
- 부사수 PC(옛 표현 "실행 PC")에서 push 금지(분기). 막히면 `git fetch origin && git reset --hard origin/main`(gitignore 자산 안 건드림).
- **★ 미커밋(untracked) 기사 JSON 유실 사고 (2026-06-13)**: `git stash --include-untracked`(pull 전 단계)는 **추적 안 된 파일을 working tree에서 stash로 쓸어담는다.** 다른 task가 `cardnews/articles/NNN_*.json`을 만들고 **커밋 전**일 때 auto-update/pull bat이 돌면 그 기사가 사라져 "article not found" → 준비/렌더 exit 1. **데이터는 stash에 보존**되어 복구 가능: `git ls-tree -r --name-only "stash@{0}^3"`로 확인 → `git show "stash@{0}^3:<path>" > <path>`로 개별 복원(통째 pop 금지).
  - **근본 원인**: **로컬 PC(개발기)에 auto-update 마커(`CODEX_VIDEO_DESK/TEMP/panel/auto_update.on`)가 켜져 있으면** 패널 켤 때마다 stash가 돈다. 로컬 PC=push only(STEP 0)이므로 **마커 꺼야 함**(`수신PC_자동업데이트_끄기.bat` 또는 마커 삭제). 부사수 PC는 켜둠이 정상.
  - **재발 방지(코드)**: `dashboard/auto_update.cmd` + `부사수PC_원클릭_셋업.bat`의 `stash --include-untracked` **직전에 기사 자동 커밋** 박음: `git add cardnews/articles` → `git -c user.email=phonespot@local -c user.name=phonespot commit -m "auto-save articles before update"`(없으면 no-op). 추적되면 stash가 못 쓸어감.
  - 운영 룰: 새 기사는 만들면 **즉시 커밋**(`기사_깃에_올리기.bat`). articles는 git 추적 대상(중복방지 DB).

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
- **★ 마이그레이션/시트삭제 후 기존 행 수식이 옛 시트 참조로 잔존 가능**(네이버_통합 GA4 전 행 0 사고, 2026-06-18). sync가 "0 광고그룹" 반환 시 기존 행 수식 미재작성 → **전 행 재작성 함수 필요**(`naver-synce.js refreshNaverGA4AllRows`, 당근 '🔄 GA4 매칭 새로고침'과 동일 개념). 또 **UTM_매핑 C열 슬러그 ≠ GA4 실측 utm_campaign**이면 수식 맞아도 매칭 0(네이버 `region`↔GA4 `region_keyword`, `mobile_carrier`↔없음, `powerlink` 미연결). 상세 = 변경이력 2026-06-18.

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
- **Phase 1 셋업 완료** (2026-06-11 16:00 KST): 로컬 `apps_script/` clasp clone(9파일) + GitHub repo `313jongmin-droid/phonespot-cardnews-video`(commit 5e0a776) + `.github/workflows/deploy-apps-script.yml`(Node 20 + clasp 3.3.0 + `clasp push --force`, paths: `apps_script/**`) + Secrets `CLASPRC_JSON`/`CLASP_JSON`. 동작 검증: workflow_dispatch 27초 성공 → Apps Script 콘솔 자동 반영 확인. **함정**: `CLASP_JSON`은 **한 줄 압축 JSON 필수** (multiline은 `JSON5: invalid character 'P' at 12:1` 에러). `rootDir="."`. `clasp push --force`는 콘솔 변경 무시 강제 덮어쓰기 → 다른 task가 콘솔 직접 수정 중이면 작업 사라짐, 책임 분담 표 엄수. 위 단원 함정 "Apps Script는 git pull로 자동 반영 안 됨"은 여전히 유효 — 단, **GitHub 측은 `git push` → Actions가 자동 `clasp push` 로 해결**(웹 배포는 별도). 멀티 브랜드 활성화는 신설 시점에 workflow step + `CLASP_JSON_<BRAND>` Secret 1줄씩 추가. 2026-06-16부터 Node 20 deprecation → `node-version` 20→24. 정본 = `ads/MULTI_BRAND_ARCHITECTURE.md` "Phase 1 셋업 완료" 섹션.

**2026-06-15 세션 — 광고운영 인프라 안정화 (상세 = `CLAUDE.md` STEP 8 + 각 정본)**
- **STEP 0 머신 모델 갱신**: 노트북 → 로컬 PC로 push 주체 변경. F단원 동기화. 정본 = `CLAUDE.md` STEP 0.
- **GitHub Actions 실패 알림**: `deploy-apps-script.yml`에 `Notify Telegram on failure` step + GitHub Secrets `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` 등록. workflow #4 `d4157c0` 29초 성공 = 알림 트리거 안 됨(=정상). 다음 진짜 실패 시점에 첫 알림 = 자동 검증. 정본 = `ads/MULTI_BRAND_ARCHITECTURE.md` "🔔 실패 알림 셋업".
- **`_secrets/` 백업 정책**: 별도 백업 비채택(사장님 결정) + 재발급 절차로 처리. **★ 핵심**: Apps Script PropertiesService 키(메타·네이버·인스타·GA4·유튜브·Gemini·Apify)는 Google 클라우드 저장 = `_secrets/` 손실 무영향. 영향 = 로컬 텔레그램 listener 정도. 정본 = `_docs/DISASTER_RECOVERY.md`.
- **`ads/README_FOR_AI.md` 갱신**: Phase 1 자동 배포 흐름 + **콘솔 직접 수정 ❌** 룰 박음. 다음 광고운영 클로드 진입점에서 즉시 파악.

**2026-06-15 세션 3 — B1 시트 read 인프라 + 당근 자동화 (상세 = `CLAUDE.md` STEP 8)**
- **B1 시트 read 셋업** (`apps_script_sheet_export/`): 별도 Apps Script 프로젝트 = 본점 generator.html doGet 충돌 0. `doGet(e)`로 시트 1개 JSON return (토큰 인증 + offset/limit). `exportAllSheetsToDrive()` = 매일 03:00 자동 30탭 → Drive 폴더 `PhoneSpot Sheet Snapshots` (ID `1M-w-Dx0oFAw8Bieq9hwiF17E-6BvWM1k`) JSON 저장 + `__meta.json` + `__headers.json` (전체 탭 첫 5행 27KB). **★ 함정**: Anthropic workspace proxy = `script.google.com` 차단 → 클로드 web_fetch 직접 호출 ❌ → Drive snapshot으로 우회 (Drive MCP read_file_content). 큰 파일(메타_통합 137KB / 네이버_통합 330KB / GA4_자동 230KB)은 토큰 한계 → `__headers.json` 단일 파일로 헤더 read. 보안: 토큰+URL = `_secrets/sheet_export_url.txt` + `sheet_export_token.txt` (.gitignore). GitHub Secret `CLASP_JSON_EXPORT`. 정본 = `ads/MULTI_BRAND_ARCHITECTURE.md`.
- **당근 자동화** (`apps_script/danggn-sync.js` 신설, 네이버_sync 패턴): API 없음 = 노출/클릭/지출 수기 + GA4 매칭만 자동. 17컬럼 단순화 (메타_통합 19컬럼에서 캠페인ID/광고그룹ID 제외): 날짜/캠페인명/광고그룹명/노출/클릭/지출/CTR/CPC/GA4세션/카톡클릭/전화클릭/시티마켓/카톡전환률/카톡당CPC/문의수/개통수/메모. 함수: `createDanggnIntegratedSheet`(시트 자동 신설), `syncDanggnGA4`(행마다 SUMIFS 수식, 매칭 키 = 날짜+`DANGGN_UTM_SOURCE`+`당근_UTM_매핑` VLOOKUP), `setupDanggnTrigger`(매일 02:30), `showUnmappedDanggnAdgroups`, `showDanggnUtmSource`. Code.js onOpen에 `🥕 당근 자동화` 메뉴 추가 (네이버 패턴 그대로). 사장님 결정: Q1=B(17컬럼) / Q2=옛 당근 시트 유지(L 조회수 M 방문고객 N 단골수 같은 당근 특화 데이터 백업) / Q3=02:30 / Q4=당근_통합 H열(=F 지출) 합산 추가. **★ 함정**: `DANGGN_UTM_SOURCE` 미등록 또는 GA4 실제 값과 다르면 매칭 0건. 통합대시보드 합산 = 17컬럼이라 지출 위치가 메타_통합(H)과 다름(F) = updateChannelMatrixWithGA4 분기 필요.

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
- listener 죽으면 outbox 쌓이기만 함(데이터 손실 X, 재시작 시 한 번에 푸시). 부팅 자동시작 = `shell:startup`에 `start_listener_silent.vbs` 바로가기(1회 셋업). **이식/PC교체 후 이 바로가기 빠지면 자동시작 안 됨 → 수동 재등록**.
- 송신 성공 = `resp_ok=True + message_id` 로그 확인(`automation/_state/listener_log.txt`). 폰 미수신 시 봇 채팅창·알림 mute·차단 점검.
- **★ listener는 반드시 truststore venv(`.phonespot_runtime\Scripts\python.exe`)로 띄울 것 (2026-06-18).** `start_telegram_listener.bat`이 `py -3`(시스템 파이썬)을 쓰면 사무실 TLS 가로채기에서 `call_api`(urllib, `telegram_listener.py:107`) 송신이 `CERTIFICATE_VERIFY_FAILED`로 실패 → outbox 잔존. 이식(06-18) SSL 해결은 venv `sitecustomize.py`의 `truststore.inject_into_ssl()`에만 적용됨(경로 고친 4파일 목록에서 이 bat 누락). `tg_send.py`도 동일 — venv로 실행해야 SSL OK.
- **진단 순서**: ① outbox에 .txt 잔존 = listener OFF 또는 송신 실패 ② `listener_log.txt` 마지막 줄 `stopped`면 데몬 꺼짐 → venv로 직접 띄워 테스트 `..\.phonespot_runtime\Scripts\python.exe -u scripts\telegram_listener.py`(~35초 내 잔존분 푸시) ③ 로그에 `[outbox] send failed ... CERTIFICATE_VERIFY_FAILED`면 venv 미사용 확정 → bat 수정.
- **.bat 편집 시 `[IO.File]::ReadAllText/WriteAllText`는 상대경로면 .NET cwd(PS 위치 아님) 기준 → 엉뚱한 폴더. 반드시 절대경로.** (ReadAllText/WriteAllText는 CRLF·인코딩 보존 = .bat 안전 편집법, Edit툴 LF변환 회피.)

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

**런타임 venv (Python/SSL) — 2026-06-18 박음**
- `.phonespot_runtime`은 venv. **Python 3.14 기반이면 `truststore`(0.10.4)가 SSL `verify_mode`에서 무한재귀 → 온라인 pip 설치 전부 `RecursionError`**(패널 `시스템 업데이트`·`SETUP_*`·직접 pip 다 막힘). 우회=**로컬 wheel 설치** `pip install --no-index --find-links <dir> <pkg>`(HTTPS 안 타 truststore 안 건드림; 순수파이썬은 Linux서 받은 `py3-none-any` wheel도 Windows 설치가능). 근본해결=런타임을 Python 3.12/3.13으로 재생성, 또는 truststore 3.14지원/제거 후 certifi. (실증: mutagen 설치가 RecursionError → `_mutagen_whl/` 로컬wheel `--no-index`로 우회.)

**리포 위생 (STEP 7)**
- 실행파일 단일 위치(SSOT), 루트 편의복사 금지. 새/수정 `.bat/.ps1` 커밋 전 중복 md5 점검.
- `.gitattributes`로 줄끝 고정 + 한글 bat BOM 정책.

---

**★ 대형파일 안전규칙 + 커밋 검증 게이트 (2026-06-14, D 적용)**
- **~31KB 도구 캡**: Edit 도구·Read·cat·grep·git show 는 ~31KB 넘는 파일을 그 지점에서 잘라 읽는다. **그 캡된 내용을 되쓰면 호스트 파일이 truncate**(매처 main 소실·bat 꼬리 소실의 진짜 뿌리). **bash-python(open/write)은 캡 없음 → 대형파일은 이걸로만.**
- **규칙(절대): 26KB+ 파일은 Edit 도구 금지, bash-python(read→`assert count==1`→write)으로만.** 매 쓰기 후 ① byte수 비교 ② `py_compile`(.py) ③ CRLF·`:end`/끝마커(.bat) 확인. **진실 확인도 Read 말고 `python -c "..open(p).read().."`**(Read·grep은 캡됨).
- **대형 추적 파일**(분할은 비추천 — 다른 task 영역이거나 쪼개도 캡 밑 안 됨, 규칙으로 관리): `apps_script/generator.html`·`ads/.../generator.html`(173KB, **광고 task**)·`server.py`(165KB, 패널)·`meta-sync.gs`(73KB)·`Code.gs`(46KB, **광고**)·`apps_script/index.html`(41KB)·`APPLY_..._V2.py`(38KB)·`codex_semantic_visual_match.py`(32KB).
- **★ 커밋 검증 게이트(D) — `CODEX_VIDEO_DESK/MAINTENANCE/codex_github_upload.py` main()**: `git add -A` 직후, 변경된 **.py 는 `py_compile`, .bat 는 ① CRLF(lone LF 0) ② 한글내용(`[\uAC00-\uD7A3]`) 포함 시 UTF-8 BOM(EF BB BF)** 검사 → 하나라도 깨지면 `git reset -q` + `return 3`(커밋·푸시 중단). **훅 정본=`.githooks/pre-commit`**(게이트3=한글bat BOM, L44-55). **★ 복구(2026-06-18 실증)**: 시스템업로드가 `LF(CRLF 아님)` 또는 `한글 .bat인데 BOM 없음`으로 ABORT 시 — 해당 .bat을 bash-python으로 CRLF 정규화 + (한글 있으면) 선두 BOM 추가(`b'\xef\xbb\xbf'+b`), 내용변경0(`git diff -w`) 확인 후 재업로드. 단 L445 'NO BOM' 절대규칙과 충돌 → **신규 .bat은 한글 본문 ASCII화가 더 안전**(BOM이 `@echo off` 앞 → 일부 cmd 첫줄 오작동 위험), 게이트 통과용 BOM 추가만 허용. stale `.git/index.lock`(직전 git 중단 잔재) → lock 에러 시 로컬 PC `Remove-Item -Force ...\.git\index.lock` 후 재실행. **편집 손상이 HEAD까지 오염되는 것을 원천 차단**(과거: 깨진 매처·bat 이 자동커밋으로 git 에 올라가 복구 난항). 정상본만 커밋되므로 git 이 항상 안전한 롤백 지점.
- **복구법 요약**: 큰 .py 꼬리 소실 = `git log -- <path>` → main 있는 커밋 블롭과 공통 앵커로 `cur[:i]+good[j:]` splice. bat 꼬리 소실 = 읽기 없이 **바이너리 append** + 전체 CRLF 정규화(`b.replace(CRLF,LF).replace(LF,CRLF)`). DB NUL 손상 = `cp`(‧`git checkout`은 .gitattributes 필터가 NUL 유발 → 우회).

## J. 기사 작성 스펙 (클로드 집필)

**목적**: 클로드가 주제선정→사실수집→기사 JSON을 일관되게 작성.

**정본**
- `cardnews/templates/article_authoring_spec.md` — cards 텍스트=영상 대본. 출력 분기: 영상(일러스트 자동매칭, 카드이미지 불필요) vs 카드뉴스(+카드이미지).
- 진입: CLAUDE.md STEP 2 "기사 써줘/주제 뽑아줘".
- **★ 영상 길이 목표(2026-06-18 갱신, 종민 결정 균형KPI)**: **30초 안팎(최대 35초)**(25초는 내용 엉성해 비채택 / 35초까진 유지율 OK). 길이는 narration/본문 글자수가 좌우 → **한 문장 ≤32자·6카드 합계 ≈220자**·**팩트 3~4개**. + **1영상=1주장**(스펙·가격·CTA 다 넣지 말 것=유지율 분산) + **cold-open**(cards[0] 헤드라인 숫자/가격 시작=첫 프레임 페이오프, 오프닝 스팅 결합이라 OPENING_SEC은 안 건드리고 집필로 달성) + **검색질의형/질문형 제목** + **시리즈 고정코너 prefix**(재방문/구독) + **하이브리드 루프 엔딩**(card_6 CTA 유지 + 마지막 narration 한 줄=오프닝 후킹 루프백; 렌더 타이밍 무수정, 대본/자막 레벨). 전부 `article_authoring_spec.md` 정본에 박음.
- **★ 후킹 공식(2026-06-13)**: 오프닝/인트로 첫 문장 + cards[0] = 설명형 ❌ → **호기심 갭/긴장형 5패턴**(질문·반전·손해회피·숫자단정·대상지목). 결론/궁금증 먼저, 과장·낚시 금지. (스펙 narration_md §후킹 공식에 박힘)

**함정**
- 기사 JSON은 git 추적 = 중복방지 DB. 새 주제는 `cardnews/articles/*.json` 중복 회피 먼저.
- **길이=코드로 못 줄임**(나레이션 TTS 길이 좌우). 56초처럼 길면 집필 단계에서 줄여야 함.

---

## 변경 이력 (이 맵 자체)
- 2026-06-14: **TTS 타이밍 graceful fallback (C단원).** 단어경계 정렬 실패(날짜/영문 발음≠글자)가 빌드를 죽이던 것 수정 → `generate_tts` char_weight_fallback 반환 + `verify_tts_timing` 게이트(char_fallback 모드 통과 + ms/window 검사 word_boundary 한정) + bat `--allow-char-fallback`. 날짜/영문 섹션만 근사싱크+경고, 나머지 정밀, 빌드 성공. 정밀=기사 한글화 레버(024 hook 검증).
- 2026-06-14: **★ 자막 정밀싱크(B)+오렌지강조 + content-gate 키워드면제 + CLIP 설치 + 한글화룰 (C·E·J단원).** ① B=`chunkUtil` 정밀모드(word_boundary)면 가독바닥 OFF→자막 발화에 정확 비례(`CasualCard`가 `_tts_timing.mode` 읽어 `precise` 전파). ② 자막강조=`CasualCaption` 작성자 `caption_emphasis`만 오렌지·정확매칭·못맞으면 스킵(자동패턴 OFF). ③ 키워드≥2 매칭은 CLIP content-gate 면제(추상 일러 거부 보완, cpt 제외). ④ CLIP(jina-clip) 설치완료(text_model snapshot_download로 채움) + 임계 0.28→0.24(bat env). ⑤ 기사스펙에 영문기능명→한글구체어 룰(`article_authoring_spec.md`). 검증: 023(한글) 주제비주얼 8개·smartphone 2·전섹션 정밀싱크 vs 022(영문) 2개·19중립 = 한글화 효과 입증. **콘텐츠 한계(영문/추상)는 임계/일러 아니라 기사집필 레버.**
- 2026-06-13: **★ 매칭 망가짐의 진짜 뿌리 = `codex_unique_illustration_guard` 버그(검증완료).** 가드가 semantic_match 뒤에 중복 중립을 유니크화하며 cpt·무관 그림을 되살림 → cpt·blocklist 제외 + 중립 반복 허용으로 수정. 재렌더 224859에서 cpt=0 확인. 포토 "일러스트보다 우수할 때만" 규칙(`photo ≥ best_ill`)도 추가. 남은 appliance/ti_decrease는 매처 약한픽/그리디 = 에셋 보강으로(함정 박음).
- 2026-06-13: **E단원에 실사 포토 라이브러리 박음 (사장님 설계).** `assets/photos/`(한글 파일명=라벨) → 매칭 1순위(`≥PHOTO_MIN` 기본 0.80, env) → 일러스트 → 생성요청. `build_photo_index`+`best_photo` 게이트, `ImageVisual`로 렌더. 텍스트 엔진만 써 CLIP 미설치여도 작동. git 비추적(렌더 PC에 직접). 함정에 "안 뜨는 3원인" 박음. **검증 대기**(사진 넣고 0.6으로 재렌더).
- 2026-06-15: **F단원 머신 모델 갱신 (G단원도 일관) — 노트북 → 로컬 PC push 주체 변경.** 사장님 운영 = 노트북은 크롬 원격 입구만, 실제 작업/git push는 로컬 PC. 머신 역할 표 4행 + 원칙 모두 갱신. Git for Windows 2.54.0 설치 사실 박�
- 2026-06-14: **커버 헤드라인 위로 당김 (C단원).** `Cover.tsx` 헤드라인 블록 `bottom:120`(맨 아래) -> `top:1180`(히어로 y1100 바로 아래 80px) — 히어로~문구 사이 빈 흰 공간 제거. 상하 위치 조정 = `top` 값만. 커버는 Step6 `render_cover.mjs`로 재생성(재렌더 필요). ※ SYSTEM_MAP이 ~65KB 읽기캡 초과 → 이 항목은 mid-insert 불가로 변경이력 끝에 append(날짜로 최신 식별).
정 + 재발급 절차 가이드 (DISASTER_RECOVERY.md 갱신).** 사장님 결정 = 별도 백업 비채택. **★ 핵심**: Apps Script PropertiesService 키는 Google 클라우드 저장 = `_secrets/` 손실 무영향. 영향 = 로컬 텔레그램 listener 정도. 정본 = `_docs/DISASTER_RECOVERY.md`.
- 2026-06-15 (세션 3): **B1 시트 read 인프라 + 당근 자동화 셋업 (G단원).** ① **B1**: 별도 Apps Script 프로젝트 `apps_script_sheet_export/` (doGet 토큰 인증) + Drive snapshot 폴더 `PhoneSpot Sheet Snapshots` (매일 03:00 30탭 JSON + `__headers.json` 27KB + `__meta.json`). **★ 함정**: Anthropic workspace proxy = `script.google.com` 차단(`X-Proxy-Error: blocked-by-allowlist`) → 클로드 web_fetch 직접 호출 ❌ → Drive snapshot으로 우회. 큰 파일 토큰 한계 → `__headers.json` 단일 파일로 모든 탭 헤더+첫 5행. ② **당근**: `apps_script/danggn-sync.js` 신설 (네이버_sync 패턴, 17컬럼 단순화, API 없음 = 수기 + GA4 매칭만, 매일 02:30). 시트 메뉴 🥕 당근 자동화. `DANGGN_UTM_SOURCE` Script Property 등록 필수(GA4 sessionSource 실제 값). 정본 = `ads/DANGGN_AUTOMATION.md` (신설 예정) + `ads/MULTI_BRAND_ARCHITECTURE.md`.
- 2026-06-15 (세션 3 검증+UX, 47e33ae): **`DANGGN_UTM_SOURCE` 정답 = `daangn`** (g 사이 `aa`). GA4 sessionSource 5/17~6/14 데이터 검증 결과. 일부 옛 `danggn` 오타 행은 소수 = 무시. GA4 영문값 표 박음(`price_check`/`sm_festival`/`sm_festa`/`a17`/`free_phone`/`region`/`kids`/`sa_01~05`). UX: 메뉴 이름 "오늘" → "**🔄 GA4 매칭 새로고침 (전체 행)**", silent return → alert(시트 없음/비어있음/갱신완료+진단 가이드+utm_source 값), 트리거 환경 try-catch. **통합대시보드 안전 처리**: `Code.js` `channels`/`trendChannels`/`ADS` 3곳 옛 당근 시트 G열 합산 유지 + 전환 옵션 주석 1줄씩 박음(다운그레이드 0, 운영 전환 시 주석 보고 1줄 갱신). 정본 = `ads/DANGGN_AUTOMATION.md` 갱신.
- 2026-06-14: **★ 매처 main 소실/복구 + 중립 로테이션 + 원자적쓰기 (검증 214114).** Edit 도구가 큰 파일(>~31KB) 꼬리를 캡해 되쓰며 `codex_semantic_visual_match.py`의 main()을 날림 → 매처가 죽어 022 사진/매칭 0(에러 없음). git 이력서 main 있는 커밋(6144576)으로 splice 복구(본문=내 수정 보존). `pick_neutral` 라운드로빈(smartphone 11→5종×3), `write_json` 원자적. **규칙: 대형 .py/.md는 Edit 금지·bash-python만.** 함정 E단원에 박음.
- 2026-06-14: **★ 대형파일 안전규칙 + 커밋 검증 게이트(D) 박음 (I단원).** ~31KB 도구캡(Edit/Read/grep) → 대형파일 bash-python only·매쓰기후 검증 규칙. `codex_github_upload.py` main()에 검증 게이트(.py py_compile + .bat CRLF, 깨지면 git reset+return3) → 손상 HEAD 오염 차단. C(물리분할)는 다른task영역/위험대비이득 적어 비채택, 규칙+D로 대체.
- 2026-06-14: **★ 일러스트도 렉시컬 키워드 신호로 안정화 + 태그DB 손상 재발방지 (E단원, 검증완료 170444).** 일러스트가 안 쓰인 진짜 원인 = ① 렌더 PC는 일러스트도 임베딩만 씀 → 해시이름+헤드라인 희석으로 정확 키워드 매칭도 임계 미달(불안정) ② 태그DB가 비원자적 write로 NUL/truncate 손상되면 read_json이 빈 DB 반환 → 라이브러리 통째 상실. 수정: ① `codex_semantic_visual_match.py` 일러스트 렉시컬 키워드(`build_illust_keyword_index`/`illust_lexical_hits`/`best_lex_ill`, hits≥`MIN_ILLUST_KEYWORDS` 기본2 → 임베딩보다 우선, 약하면 임베딩 유지=무회귀) ② `codex_illustration_db.py` `write_json` 원자적(temp+os.replace). 검증: mid_release/official_sale/mounted_body 키워드대로 제자리, smartphone 6→4, PNG 전부 존재(깨짐0). 함정에 DB손상·stale포토·마운트괴리 박음.
- 2026-06-14: **★ 포토 매칭 = 임베딩 폐기 → 렉시컬 모델명 일치로 전환 (E단원 갱신).** 한글 임베딩이 모델명(갤럭시A/엑시노스/S25)을 못 구분(렌더 증거: 플립청크에 갤럭시A, 엑시노스청크에 S25, 통신사로고 곳곳) → 정답·오답 점수가 ~0.5에 겹쳐 PHOTO_MIN 임계 무의미. 신호를 렉시컬로 교체: `_photo_tokens`/`_is_distinctive`/`photo_lexical_score`/`PHOTO_STOP`, `best_photo=(dist,gen,file)`, chosen 0순위 = **구별토큰 dist≥1**. 일반토큰(삼성/갤럭시/로고)만으론 미채택 → `갤럭시A`·`S25`가 무관 영상에 안 붙음(커버 오염 차단). **임베딩 불필요 → 부사수PC(모델 미설치)에서도 작동.** 021 검증: 엑시노스→엑시노스, 플립→플립, 배터리→배터리 정확. **필수 일러 추천 `MAX_REQUESTS` 3→5**(`codex_illustration_scout.py`, graceful degradation). 교훈: 임계값은 정답>오답 간격 있을 때만 작동, 겹치면 신호를 바꿔야 함. **함정: `codex_illustration_scout.py` Edit 누적 truncation → git HEAD 꼬리로 복구.**
- 2026-06-13: **고퀄 batch 박음 (재렌더 181856 검증).** C단원: 오프닝 2.0초·아웃트로 3.2초(+2)·**닫기 CTA 디자인카드 `CasualCta`(일러스트 폐기)**·카드 전환 애니메이션(`cardEnter`). J단원: 후킹 공식 5패턴. (1 CLIP·9 제품이미지는 제외/대기.)
- 2026-06-13: **C단원 SNS 레이아웃·오디오 + J단원 길이목표 박음 (P2·P3).** 제목바 hook-only(`CasualCard.tsx`), 자막 세이프영역 안전(변경X), 라우드니스 −14(`finalize_sns_video.py` loudnorm, env off), BGM 보류. 길이 35~45초 목표 = 기사 집필 레버(`article_authoring_spec.md` §body + J단원). 검증=실행PC 재렌더.
- 2026-06-13: **E단원 의미매칭 범용수정 + C단원 후킹 박음 (SNS 품질점검발).** 중립폴백 정상화·EMBED_MIN_ILLUST 0.48·content-gate(CLIP 미설치면 무력)·미검증 cpt_ 텍스트매칭 제외(`_is_unverified_concept`, 카테고리 규칙·env). 함정에 CLIP 의존성·비-cpt 오배치는 데이터교체 박음. C단원 후킹=`OpeningHook.tsx`(다크+주황글로우+키커 pill, OPENING_SEC 1.5→1.1).
- 2026-06-13: **A단원 패널 UI 단계적 노출 박음(v31~v32)** — 영상작업 보조버튼 2묶음을 공통 `.foldbar` 접기 토글(보기·편집 + 라이브러리·시스템 관리, 둘 다 기본 접힘·동일 UI·캐럿)로 → 첫 화면에 상태+로그 노출. 보기·편집은 `localStorage panel.viewEdit` 기억. 런타임 4박스 슬림. PANEL_VERSION v30→v32.
- 2026-06-13: **A단원에 패널 iOS 디자인 시스템 박음(v25~v30)** — 토큰/Pretendard/legacy alias/풀폭 거터/sticky 좌측리스트/우측 페어(상태\|로그·기록\|결과)/2줄 슬러그행(idx+1)/상단 흰카드+컬러점/그림자 단일화. 함정에 **Edit 누적 truncation 실사고 + bash-python 작업법 + 복구법** 박음. 롤백=`server.py.bak_pre_ios_20260613`.
- 2026-06-15: **F단원 머신 모델 갱신 — 노트북 → 로컬 PC push 주체 변경 (CLAUDE.md STEP 0 2026-06-15 갱신과 동기화).** 머신 역할 표 4행(로컬 PC=push only / 노트북=크롬 원격 입구만, git ❌ / 부사수 PC=pull only / 메인 PC=자산 소스), 원칙·git 탐색·함정의 옛 "노트북=push" 표현을 새 모델로 갱신. **Git for Windows 2.54.0 설치 사실(Phase 1 셋업 2026-06-11)** 박음 — 옛 함정 "노트북엔 Git for Windows 없음"은 다른 머신 셋업 시 참고용으로 보존(통째 삭제 X). **광고운영 트랙 자동 배포 흐름** (`apps_script/` 수정 → git push → GitHub Actions → clasp push --force → 콘솔 자동 반영, **콘솔 직접 수정 ❌**) 명시. `노트북_깃허브_올리기.bat` 파일명은 옛 모델 잔재 — 실제 용도는 로컬 PC 전용 push로 갱신.
- 2026-06-15: **GitHub Actions 실패 알림 셋업 (G단원, 정본 = `ads/MULTI_BRAND_ARCHITECTURE.md`).** `deploy-apps-script.yml`에 `Notify Telegram on failure` step 추가(`if: failure()`, 카드뉴스용 봇 재활용). GitHub Secrets `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` 등록 완료. CLASPRC_JSON 토큰 만료 / clasp push 에러 / Node 24 deprecation 등 자동 감지 → 텔레그램 알림(리포·브랜치·SHA·실행자·Actions run 직링크). 성공 알림 X(노이즈 차단). 멀티 브랜드 step 확장 시에도 단일 알림 step이 모든 failure 캐치 = 추가 작업 0.
- 2026-06-15: **`_secrets/` 백업 안 함 결정 + 재발급 절차 가이드 (DISASTER_RECOVERY.md 갱신).** 사장님 결정 = 별도 백업 비채택 (HDD 손상 확률 낮음 + 재발급 45분~1h 감수). DR 가이드의 "백업 필수" 섹션 → "손실 시 재발급 절차"로 통째 갱신. 키별(META_TOKEN / NAVER_API_LICENSE+SECRET_KEY / GEMINI / APIFY / TELEGRAM) 발급 URL + 절차 + 등록 위치 박음. **핵심 사실 박힘**: Apps Script PropertiesService 사용 키(메타·네이버·인스타·GA4·유튜브·Gemini·Apify)는 **Google 클라우드 저장 = `_secrets/` 손실 무영향**. 영향 받는 건 로컬 텔레그램 listener 정도. CLASPRC_JSON/CLASP_JSON은 GitHub Secrets 저장 = PC 손상 무관. 시나리오 A/B의 "_secrets/ 백업에서 복원" → "재발급 절차" 안내로 갱신. 한 줄 요약 + 매트릭스 + 정직한 한계 일관 정리.

- 2026-06-16: **★ UTM_매핑 통합 시트 코드 적용 + 배포실패 복구 (G·I단원).** UTM 통합 시트(6컬럼: 채널/광고그룹명/utm_campaign/첫발견일/상태/메모) 사장님 마이그레이션 후, ① `apps_script/meta-sync.js` SUMIFS VLOOKUP → **FILTER(채널="페북")** + `autoDiscoverAdsets_`/`showUnmappedAdsets` 6컬럼 표준화(채널 드롭다운 박음, 채널="페북" 행만 신규/검사). ② `apps_script/naver-synce.js` `SHEET_NAVER_UTM_MAPPING='UTM_매핑'` 통합 + SUMIFS FILTER(채널="네이버") + `ensureNaverUtmMappingSheet_`/`autoDiscoverNaverAdgroups_` 통합 시트 표준 + `showUnmappedNaverAdgroups` 정의 추가. ③ `apps_script/danggn-sync.js`는 직전 세션(commit ef19fa9) 이미 통합 적용 완료. **★ 함정 재발(I단원)**: Edit 도구 누적 → `meta-sync.js` 1665→1659 / `naver-synce.js` 652→650 / `Code.js` 935→919 (한글 깨짐) / `youtube_sync.js` / `danggn-sync.js` 모두 끝부분 truncation → `node --check` SyntaxError → GitHub Actions 배포 실패 → 텔레그램 알림(2026-06-15 셋업한 알림 첫 실제 작동 사례). 복구 = `git show HEAD:apps_script/<파일> > <파일>` + bash-python 으로 변경만 재박음 + `node --check` 5개 .js PASS 검증. **★ 규칙 재확인**: 26KB+ Apps Script 파일 = Edit 금지·bash-python only(I단원 규칙이 이번에도 적중). bash commit은 권한 불가(`.git/objects` Operation not permitted) → 사장님 PowerShell에서 `git add apps_script/meta-sync.js apps_script/naver-synce.js && git commit -m "fix(utm): 통합 적용 (배포실패 복구)" && git push` 필요. 옛 시트 `네이버_UTM_매핑`/`당근_UTM_매핑`은 마이그레이션 함수가 통합 후 자동 삭제. 정본 = `ads/MULTI_BRAND_ARCHITECTURE.md`(통합 시트 구조).
- 2026-06-16: **C단원 — 오프닝 후킹 스팅 BGM 박음.** `Composition.tsx` 루트(오프닝 Sequence 밖=0초부터) casual 한정 `<Audio music/opening_sting.mp3 vol .7>`. 에셋 3.0초·페이드인없음·2~3초 페이드아웃, 오프닝 2초 고정(`OPENING_SEC=2.0`)과 정합(매 영상 동일). `*.mp3` git 비전파 → 렌더PC `shorts/public/music/`에 직접. 코드는 git 전파, 번들 자동 재빌드(패널 재시작 불필요). 기존 BGM 보류 노트 옆에 추가.
- 2026-06-16: **E단원 — 수동 라이브러리 등록 절차 박음.** 매처는 DB 순회(파일명 아닌 keywords가 신호)라 ILLUSTRATION_DROP 떨구기만으론 매칭 X. DB 엔트리(available:true)+`<variant>.png` 둘 다 필요(둘 다 git 추적). `camera_quality`/`document_article`/`fast_charging`/`battery_capacity` 4개 등록. 텍스트 박힌 그림은 keywords 좁히기.
- 2026-06-16: **C단원 — CTA 스팅 추가(검토대기).** 오프닝 스팅에 더해 닫기 CTA(`ctaStart`)부터 5초(0~4초 풀·4~5초 페이드아웃, vol 0.6) `cta_sting.mp3` 깔기(`Composition.tsx:82-87`, casual 한정). 두 스팅 모두 트랙 앞부분(북엔드). `*.mp3` git 비전파 → 렌더PC 직접. 사장님 검토 = 익일.

- 2026-06-17: **★ 인스타 자동화 복구 + 마이그레이션 컬럼 시프트 사고 + UTM 통합 후속 (G단원).** 
  - **① 인스타 syncInstagramDaily 함수 복구.** 2026-06-11 사장님이 콘솔에서 직접 박은 인스타 함수가 = Phase 1(clasp push --force) 첫 push 시점에 통째 덮어쓰여 사라짐(6/10 마지막 데이터 후 함수 부재). git 이력에 한 번도 박힌 적 없음 확인. 신규 작성 + git push: `apps_script/meta-sync.js`에 `syncInstagramDaily`/`backfillInstagramAll`/`syncInstagram_`/`fetchInstagramMedia_`/`getInstagramBusinessId_` 함수, `SHEET_INSTAGRAM='인스타'` + `INSTAGRAM_DATA_START_ROW=4` 상수, setupTriggers 매일 02:00 트리거 등록, 메뉴 📷 인스타 동기화/⏪ 인스타 전체 백필 추가. **사장님 결정 4개**: ① 전부 가져오기 ② 초기 1회 전체 / 다음 7일 (`mode='auto'`: 시트 비어있으면 전체, 데이터 있으면 7일) ③ I비고/B포맷 공백 보존 ④ 4행부터 시작. 매칭 키 D열 permalink (기존 행 E·F·G만 갱신 / 신규 append timestamp 오름차순). insight metric = `views` (미지원 시 reach 폴백, Reels/Image/Video 통합). 검증: 38개 게시물 정상 박힘(2025-06-02 ~ 2026-06-16). **★ 룰 재확인 + 박힘**: 콘솔 직접 수정 = clasp push --force로 덮어씌워짐 = 함수 영구 손실. 모든 코드 = git에 박혀야 살아남음 (Phase 1 함정 = 또 한번 적중).
  - **② 마이그레이션 컬럼 시프트 사고 + 해결.** `migrateUtmMappingsUnified()`가 `insertColumnBefore(1)`로 UTM_매핑 A열에 채널 컬럼 추가 → **Google Sheets 자동 시프트로 다른 시트(메타_통합·네이버_통합·당근_통합)의 모든 SUMIFS/FILTER 수식 UTM_매핑 컬럼 참조가 한 칸 밀림** → 옛 `FILTER('UTM_매핑'!B:C, 'UTM_매핑'!A:A="채널")` → 시프트 후 `FILTER('UTM_매핑'!C:D, 'UTM_매핑'!B:B="채널")` (B:B = 광고그룹명 컬럼 = 채널값 매칭 0) → FILTER 빈 결과 → VLOOKUP "" → SUMIFS 0. **증상**: 당근_통합 K~O열 = 전부 0(사장님이 메뉴 🔄 GA4 매칭 새로고침 실행해서 새 코드 SUMIFS 수식 박혔는데 깨진 상태). 메타·네이버 통합 = 옛 캐시 값만 보여 일시적 정상으로 보임. **진단 결정타**: 빈 셀에 직접 SUMIFS 박았더니(`=SUMIFS('GA4_자동'!G:G, 'GA4_자동'!A:A, 20260616, 'GA4_자동'!B:B, "daangn", 'GA4_자동'!D:D, "price_check")`) = 값 나옴 → SUMIFS 자체와 GA4 데이터 정상 → 시프트 깨짐만 원인. **해결**: 메뉴 🟠 당근 자동화 → 🔄 GA4 매칭 새로고침 (전체 행) 실행 → `syncDanggnGA4()` 함수가 새 SUMIFS 수식 모든 행에 다시 박음 → 깨진 옛 수식 덮어쓰기 → 매칭 정상화. 검증: 사장님 "아 해결됐다". **★ 재발 방지 룰 박음**: 컬럼 구조 변경 마이그레이션 함수(특히 `insertColumnBefore`/`insertColumnAfter` 사용 시) = 함수 끝에 **다른 시트의 SUMIFS 수식 박는 sync 함수들 자동 호출 추가 필수** (`syncMetaCampaignIntegrated` / `syncNaverIntegrated` / `syncDanggnGA4({interactive:false})`). 또는 사장님에게 알림 박스에 "다음 단계 = 메뉴 🚀 전체 새로고침 1회 실행 필수" 안내 박음.
  - **③ DANGGN_UTM_SOURCE 정답 재확인**: `daangn` (g 사이 `aa`, 2026-06-15 박힘) — 사장님 콘솔 등록 확인 = OK. 미등록·`danggn`이었으면 다른 원인이었을 것이지만 = 등록 정상.
  - **④ 데이터 검증**: (7).xlsx 분석 = UTM_매핑 6열 통합 완료(R35~R38 당근 4개 매핑 박혀있음), 옛 당근_UTM_매핑·네이버_UTM_매핑 시트 자동 삭제 완료, 당근_통합 광고그룹명 7개 중 4개 매핑됨(3개 누락 = 소식_기종가격확인 / 리틀리_가격확인_260610 / 소식_가격확인_아이폰 = 사장님 결정 후 수기 박을 것). UTM_매핑 R18~R24 = 컬럼 한 칸 어긋남(A='페북' / B='페북' / C=광고그룹명, 옛 5컬럼 시기 박힌 행에 마이그레이션이 채널 시프트로 박은 결과 = autoDiscoverAdsets_ 다시 돌면 정리됨, 또는 수기 삭제).

- 2026-06-17 (세션 2): **광고그룹별 성과 추이 차트 합류 (G단원, 사장님 직접 사용자 건의 반영).** 신규 파일 `apps_script/adgroup-trend.js` + `Code.js` onOpen에 메뉴 빌더 호출 1줄 추가(`buildAdgroupTrendMenu_`). **통합대시보드 R60~R130 영역**(R60 병합헤더 / R61 토글 B채널·E광고그룹·H기간 / R62 안내 / R63 데이터헤더 8컬럼 / R64~R93 데이터 30일 / R95~ 라인차트 multi-axis / W60 동적 광고그룹 unique 리스트). **사장님 결정 4개**: ① 기간 = **7일/14일/30일** (3일은 광고그룹별 일자 데이터 1~3건 = 노이즈 너무 커 비채택) ② 차트 = **1개 multi-axis** (CTR·문의율 좌축% + CPC 우축원, 자세한 건 각 통합 시트에서 보면 됨) ③ 채널+광고그룹 = **2단 종속 드롭다운** (W60 = `IF(B61="메타", UNIQUE(FILTER(메타_통합!E2:E,...)), IF(B61="당근", UNIQUE(FILTER(당근_통합!C2:C,...)), UNIQUE(FILTER(네이버_통합!E2:E,...))))`, B61 채널 변경 시 자동 갱신) ④ 구현 = **Apps Script** (재현 가능 + git 추적 + 다음 마이그레이션 깨짐 위험 0). **문의율 정의 = 사장님 = 문의수 / 카톡클릭** (카톡 들어온 사람 중 실제 문의 비율). 채널별 컬럼 매핑 = `ADGROUP_TREND_CHANNELS` 상수 (메타: A날짜/E광고그룹명/F노출/G클릭/H지출/L카톡클릭/R문의수 / 당근: A/C/D/E/F/J/P+Q합산 / 네이버: 메타와 동일). 메뉴 = 📊 광고그룹 추이 → 🆕 차트 셋업 (1회) + 🔄 추이 갱신. **유저 워크플로**: R61 토글 3개 변경 후 메뉴 🔄 클릭 → R64~R93 데이터 + 차트 자동 갱신. **함정**: ① 차트가 R63 헤더 + 데이터 범위 4개(날짜/CTR/CPC/문의율) 비연속 addRange로 만듦 → setupAdgroupTrendChart() 재실행 시 = 기존 차트 R63~R94 영역 hit 차트 제거 후 새로. ② 광고그룹 선택 X시 = R64에 "⚠️ 채널 + 광고그룹 선택 필요" 안내. ③ 검증 = 사장님 콘솔 셋업 후 토글+갱신 실행 후 데이터+차트 확인 필요(가이드 박는 시점 = 검증 전).
- 2026-06-18 (광고운영): **★ 네이버_통합 GA4 매칭 전 행 0 복구 패치 + 슬러그 불일치 발견 (G단원).** 증상=네이버_통합 317행 GA4세션·카톡·문의 전부 0. 원인=수식이 **삭제된 옛 `네이버_UTM_매핑` 시트** VLOOKUP 참조(메타는 통합 `FILTER('UTM_매핑',채널="페북")`로 정상). 코드(`apps_script/naver-synce.js:412`)는 06-16에 통합 수식으로 고쳤으나 `syncNaverIntegrated`가 "0 광고그룹"(네이버 집행 중단 06-16~) 반환 → 기존 05-13~06-15 행 수식 미재작성 → 옛 수식 잔존. **패치**: `naver-synce.js`에 `refreshNaverGA4AllRows()` 추가(데이터 전 행 K~S(11~19) 수식을 통합 UTM_매핑 기준 재작성) + 메뉴 `🟢 네이버 자동화 → 🔄 GA4 수식 전체 재작성 (매핑 복구)`. `node --check` PASS(격리 함수). 사장님 실행 = git push(`git add apps_script/naver-synce.js`만; 리포 미커밋 132개 있음) → Actions clasp 배포 → 시트 메뉴 1회 클릭. **★ 별도 발견 — 네이버 슬러그 불일치**: GA4_자동 실측 네이버 utm_campaign = `powerlink`(122,최다)·galaxy·phonespot·iphone·old_model·**region_keyword**(17)·holyland·kids_phone·senior_phone. UTM_매핑 C열 `region`↔GA4 `region_keyword`, `mobile_carrier`↔GA4 없음, `powerlink`↔미연결 → **수식 패치로도 이 3개는 0**, C열 값을 GA4 실측으로 교정해야 함. **시트 read 방식**: Drive B1 스냅샷(`PhoneSpot Sheet Snapshots`, 2026-06-18 03:09 KST) JSON을 **`download_file_content`(base64)→bash `base64 -d`→jq**로 read. read_file_content는 마크다운 이스케이프(`\_`·`\[`)로 JSON 깨짐 → 큰 시트는 download base64가 정답. **함정**: 65KB+ SYSTEM_MAP·CLAUDE.md = Edit 도구 truncation → bash-python으로만 편집(쓰기는 호스트 도달=git 인식). naver-synce.js(24.97KB) 호스트 Edit 후 bash 마운트가 잘린 사본(24974B) 보임=tearing(git diff는 정상) → 격리 함수 node --check + 호스트 Read로 검증. 미매핑 UTM(당근 3·메타 영상 2) GA4 실측 추천초안 = `outputs/광고운영_점검_2026-06-18.md`(소식_가격확인_아이폰→`a17`, 소식_기종가격확인→`price_check` 등, 사장님 확정 필요).
- 2026-06-18 (광고운영 2차): **UTM_매핑 정비 함수 2개 (G단원, "고치자" 1차).** `apps_script/meta-sync.js`에 `cleanupShiftedUtmRows()`(B=채널값 시프트 잔재 행을 아래→위 삭제, signature=광고그룹명 칸에 페북/네이버/당근/구글/카카오) + `flipMappedUtmStatus()`(C utm 채워졌는데 상태 ⚠️/공백 → '✅ 매핑됨', 시프트행·안내행※·utm빈행 제외 → cleanup 전 실행�
- 2026-06-18 (광고운영 3차): **1회성 메뉴 정리 (G단원, 종민 결정).** 적용 완료된 1회성 함수+메뉴 제거: `cleanupShiftedUtmRows`(meta-sync.js 🧹 시프트 정리) / `refreshNaverGA4AllRows`(naver-synce.js 🔄 GA4 재작성) / `migrateUtmMappingsUnified`(danggn-sync.js 🔄 UTM 통합 마이그레이션 — 재실행 시 `insertColumnBefore` 컬럼 시프트 재발 위험이라 제거가 오히려 안전). **유지**: `flipMappedUtmStatus`(meta ✅ 상태 갱신) + 차트셋업·시트신설·라벨링·백필·표준화·당근 🔄 GA4 매칭 등 재실행 안전 도구. 셋 다 node --check PASS·중괄호 균형·인접 함수 보존. **편집 함정(I단원)**: naver-synce.js는 호스트 Edit 후 마운트가 torn 사본 서빙 → bash-python read도 잘림 → Edit 도구(호스트)로 제거. meta/danggn은 마운트 정상이라 bash-python. push = apps_script 3파일.
rdnews/scripts/update_content_guide.py`로 §2 발행인덱스 자동 재생성, `run_windows.py:267-279`에 렌더 성공 후 best-effort 호출(학습루프 강제). ② `cardnews/scripts/validate_article.py` 기사 스키마 2단 검증(ERROR/WARN)+`--next`(현재 026). 실측 23 OK / 2 WARN(001·002 content_type 누락) / 0 ERROR. 해시태그 정규식은 마크다운 `## ` 허용으로 보정. ③ 메타_인사이트 시트화 = 새 clasp 파일 `apps_script/meta-insights-sheet.js`(기존 meta-sync.js 무수정, 전역 스코프로 상수 재사용). 배포+1회 setup 후 시트 생성 → STEP1 #8 작동. ④ CLAUDE.md STEP8(174줄=파일 40%, 광고운영이 그중 47%) → `_docs/CHANGELOG.md` 분리 = 종민 PowerShell(92KB Edit 위험으로 클로드 직접 X). **점검 발견(미반영, 종민 결정 대기)**: 레거시 무번호 기사 17 + `chrome_auto_test`(테스트 잔재)·`voice_phishing_care`(빈 스텁) 제거 권고; `automation/scripts/night_daemon.py` 자동렌더 'Day4 예정' 미완. **함정 재확인(I단원)**: 이 세션 bash·`.git` 쓰기 차단 → 신규 5파일(content_guide.md·validate_article.py·update_content_guide.py·run_windows.py·meta-insights-sheet.js) commit·push는 종민(PowerShell). 65KB+ SYSTEM_MAP·92KB CLAUDE.md = Edit 호스트 실파일은 정상이나 bash 마운트 tearing → 검증은 호스트 Read.
- 2026-06-19 (수집 성과 기준 재정의 — B단원, 사장님): 콘텐츠 수집 후보 가중치 = **유튜브 영상 조회수(`유튜브_인사이트`) + 인스타 게시물·릴스 성과(`인스타` 시트/Drive 스냅샷)** 기준. **메타(광고)는 수집에서 제외** = 광고 카피용(G단원)이지 발행 주제 선별용 아님. 가중치 매트릭스 `meta` → `insta`(insta+30% Top게시물·릴스 / insta+20% 릴스 포맷). 갱신처: SYSTEM_MAP B 가중치, INSTRUCTIONS 사전점검, PREFLIGHT. **자동화 안 함(사장님 결정 2026-06-19)**: 인스타_인사이트 MD 자동생성기는 만들지 않음. 수집 때마다 `유튜브_인사이트` + `인스타` 시트(스냅샷) 직접 보고 잘 되는 주제/라인에 가중치 → 반복으로 정밀화(탐색→착취). 인프라보다 운영 반복이 핵심. **★ 성과 피드백은 클로드 자율 = 사장님이 "이게 잘됐다" 말해주는 게 아니라, 매 수집 시 클로드가 시트에 쌓인 조회수·도달을 직접 읽어 발행 슬러그·라인과 대조해 스스로 가중치 결정.** 사람 수동 피드백 대기 금지. **CLAUDE.md STEP1 #8(메타_인사이트)도 인스타로 갱신 필요 = 종민(92KB Edit 위험).**
- 2026-06-22 (git push 텔레그램 알림 — F/H단원, 사장님): 신규 워크플로 `.github/workflows/notify-push.yml` — main 브랜치 **모든 push**(카드뉴스·문서·apps_script) 완료 시 텔레그램 알림(✅ 리포·작성자·커밋메시지·SHA). Secrets `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` 재사용(2026-06-15 배포 실패알림용 등록분). 인젝션 방지 = 커밋메시지는 env(`CM`)+`printf %s`로 전달. 기존 `deploy-apps-script.yml`(실패만 알림)과 별개 = push 성공 알림 추가. 이 파일을 push하는 순간부터 작동(첫 push가 셋업 검증).
- 2026-06-22 (날짜 기준 = env 확정 + 브랜드 통일 — B단원, 사장님): **bash 샌드박스 시계가 06-19에 드리프트**돼 실제 06-22를 2회 오인. → **날짜 기준은 env 'Today's date'(사장님 머신)만 신뢰, bash date/`TZ=...date` 금지.** `news_d7_filter.py`는 `--today <env날짜>` 명시 실행. **브랜드 통일**: '폰스팟 광교점'→'**휴대폰성지 폰스팟**'(검색키워드 정합). caption_template 매장정보(상호·카카오톡 @휴대폰성지폰스팟)·해시태그 #휴대폰성지폰스팟 반영. **카드6 영문 `source`는 `Phonespot 광교점` 유지**(사장님 028 직접수정 기준). 신규 발행물부터 적용, 기존 001~025 소급 안 함.
- 2026-06-19 (신규 라인 첫 발행 028~032 + caption 톤 박음 — B단원): pick 3건(효도폰 3종비교·갤vs아이폰 카메라·신제품vs구형 지원금)·meme 2건(호구 체크리스트5·통신사 안 알려주는 것3) 발행, 게이트 통과(스키마/회피/사전승낙서/카드6 source/narration 청결). `caption_template.md` 라인 톤표 + 해시태그 풀에 pick/meme/life 추가(신규 라인 캡션 후크 정본). 다음 번호 033~.
- 2026-06-19 (채널 육성 라인 확장 — B단원, 사장님 전략): IT뉴스 단발 외 YT·인스타 구독/바이럴 육성 위해 카드뉴스 라인 4→7로 확장. 신규 `pick`(비교추천)·`meme`(공감밈·체크리스트)·`life`(시즌·생활활용), 모두 D-7 제외(시점무관). **전략 = 초기 탐색(7라인 골고루)→조회수 데이터 보고 정밀화(탐색→착취)**, 라인별 성과는 content_guide §3 누적. 매장 비하인드(직원·개통과정)는 실사 촬영이라 자동생성 X = 사장님 촬영+AI 캡션 별도 트랙. 코드: `validate_article.py` `VALID_TYPES`에 pick/meme/life 추가. 정본 = `INSTRUCTIONS_CARDNEWS.md` "라인 5~7". 회피 키워드·매장정합 동일 적용.
- 2026-06-19 (수집 기준일 KST 정정 — B단원, 사장님 지적): 세션이 06-18로 잡고 작업했으나 KST·UTC 모두 이미 06-19(`TZ=Asia/Seoul date` 확인). 원인 = `currentDate` stale + `news_d7_filter.py`가 `date.today()`(UTC) 사용 → 한국 0~9시 하루 밀림. 조치 = 필터를 `timezone(+9)` KST 고정(`kst_today()`, `--today` 수동지정 유지). B단원 함정에 "수집 기준일=KST, 시작 시 TZ=Asia/Seoul date 확인" 박음. 영향 = 후보 판정 거의 동일(A37 D-0→D-1, 삼성보안 D-3→D-4 여전히 통과), D-N 라벨만 하루 당겨짐. ※ 026·027 `publication_date`는 06-18로 박힘 → 06-19로 정정할지 사장님 결정 대기.
- 2026-06-18 (텔레그램 송신 "기능 없어짐" 진단 — H단원): 증상=수집/발행 outbox 떨궈도 폰 미수신. 원인 2중 = ① listener 데몬 OFF(로그 09:58 start→10:46 stopped, 이식 후 `shell:startup` 자동시작 바로가기 빠짐) + ② `start_telegram_listener.bat:12`가 `py -3`(시스템 파이썬) 사용 → 이식 SSL 해결(`.phonespot_runtime` venv truststore)을 안 탐 → 송신 `CERTIFICATE_VERIFY_FAILED` 가능(코드·outbox watcher는 정상, "기능 없어짐"의 실체는 실행환경). 조치 = bat을 `..\.phonespot_runtime\Scripts\python.exe`로(종민 PowerShell `[IO.File]` **절대경로**로 CRLF 보존 수정) + venv로 직접 띄워 잔존 2건 푸시 + `shell:startup` vbs 재등록. 함정 H단원에 박음(venv 필수·진단순서·.bat 절대경로). **별도 함정**: `[IO.File]::ReadAllText` 상대경로는 .NET cwd(C:\Users\<user>) 기준이라 엉뚱한 파일 읽고 빈 파일 씀(종민 1차 시도 실패 사례).
- 2026-06-18 (전역 가이드 강제 — 사장님 지적 "가이드 어기는 게 가능하면 소용없다", 전 트랙 적용): **honor-system → 코드 게이트 전환. 정본 = `_docs/PREFLIGHT.md`.** 원인 = 룰이 "읽기로 되어 있다"에만 의존, LLM은 확률적 준수라 누락 반복(함수 유실·Edit truncation·컬럼 시프트·이번 news D-7 누락 전부 동일 종류). 진단 = self-read 강제도 LLM 의존이라 샌다 → **결정론적 강제는 부수효과 직전 코드 게이트뿐.** 신설 4종: ① `.githooks/pre-commit`(commit 관문, 전 트랙: .js/.py 문법+한글.bat BOM+카드뉴스 기사스키마 ERROR 차단, 활성화 `git config core.hooksPath .githooks`, 우회 `--no-verify`) ② `.github/workflows/deploy-apps-script.yml` "Syntax gate" step(배포 관문, 깨진 .js가 clasp push 도달 차단, node --check 전체) ③ `cardnews/scripts/validate_article.py`(발행 관문, 기사 필수키 ERROR) ④ `cardnews/scripts/news_d7_filter.py`(수집 관문, news 보도일 D-7 계산 강제 — 눈대중 금지, 검증: A37 D-0 PASS / LGU+ D-66·루머 불명·미래 REJECT). 보조 = PREFLIGHT §1(명령 트리거 시 트랙 가이드 Read+절대룰 복창). **환경 제약**: 이 세션 .git/bash 쓰기 차단 → hook 활성화·CLAUDE.md 최상단 PREFLIGHT 포인터·commit/push는 종민 로컬(PowerShell). **한계(정직)**: 수집 D-7 필터를 "돌리는" 것 자체는 아직 self(파이프 구조화 전), commit/배포/발행 관문은 코드로 진짜 강제. 강제 끝단 = 룰 복창에 대한 사장님 검수.
- 2026-06-18: **I단원 — 커밋게이트 '한글 .bat BOM 필수' + 복구레시피 박음(C단원 렌더경로 오타 동시수정).** 게이트(`codex_github_upload.py`→`.githooks/pre-commit` L44-55)는 .bat CRLF뿐 아니라 한글내용 .bat에 UTF-8 BOM도 강제. 실증: `run_youtube_sync.bat`·`cardnews/show_guide.bat`·`shorts/show_guide.bat` 3개가 LF→ABORT→CRLF로 고치니 BOM-ABORT→CRLF+BOM(내용변경0)으로 통과. C단원 L167 렌더경로 `shorts/`→`shorts/scripts/render_remotion_fast.mjs` 수정.
- 2026-06-18 (광고운영 기능확장 STEP1-3, 종민 로드맵 승인분): **데이터 정합성 + 스케줄 + 알림 (G단원).** **STEP1 UTM 정합성**: ① `Code.js refreshUtmSlugDropdowns()`(GA4_자동 실측 utm_campaign을 UTM_매핑 C열에 채널별 드롭다운, 오타/슬러그 불일치 차단) + 메뉴 🏷️. ② named range `UTM_CH`(A열)·`UTM_KEYVAL`(B:C) = `ensureUtmNamedRanges_()`(idempotent, sync/refreshAll 시작 시 자동 생성) + 메뉴 🔗 + `setupUtmNamedRanges()`. 메타(`meta-sync.js:329`)·네이버(`naver-synce.js:412`)·당근(`danggn-sync.js:280`) 수식을 `FILTER('UTM_매핑'!B:C,A:A=…)` → **`FILTER(UTM_KEYVAL, UTM_CH=…)`** 전환 = 컬럼 삽입/이동 시 명명범위 자동추적 → 6-17 마이그레이션 시프트 사고 구조적 차단(P2-5+6 통합). **STEP2 스케줄**: refreshAll 트리거 안전화(`const ui` → `let ui=null; try getUi catch` + `if(ui)` 가드 + logSync_) → 야간 트리거 가능. `setupRefreshAllTrigger()` 매일 02:45(개별 sync 01:30~02:30 다음) + 메뉴 ⏰. `adgroup-trend.js setupAdgroupTrendTrigger()` 매일 02:50 + refreshAdgroupTrendChart ui 가드. **STEP3 알림(신설 `alerts.js`)**: `tgSend_`(텔레그램, Script Property TELEGRAM_BOT_TOKEN+TELEGRAM_CHAT_ID 필요, 미등록 시 스킵) / `runHealthCheck_`(메타·네이버·당근 통합 최신일·GA4세션 전행0 감지 = 침묵실패 포착, refreshAll 끝에 호출) / `checkAdTargets_`(어제 CPL>TARGET_CPL 기본5만원 or 지출30000+문의0 경고) / `sendMorningBriefing`(매일 09:00 KPI 브리핑) + `setupMorningBriefingTrigger` + `testTelegram` + 메뉴 🔔. Code.js onOpen에 `buildAlertsMenu_` 등록. **검증**: 6파일 전부 node --check PASS, 각 치환 count==1, 옛 `FILTER('UTM_매핑'!B:C` 0건. **편집법**: Code.js(46KB)·meta-sync(83KB)는 bash-python(마운트 정상 확인 후), 신규 alerts.js는 Write. **★ 배포 후 활성화 필수(메뉴 1회씩)**: STEP1 🏷️드롭다운+🔗named range / ST
- 2026-06-18: **렌더 '배정 대기' 고착 진단·해결 + 런타임 truststore 함정 (A·I단원).** 원인=로컬 워커가 `mutagen` 미설치로 readiness 실패→5초 재확인만 하며 잡 claim 안 함(워커는 살아있음, UI '배정 대기'). 발견 막힘=런타임 venv가 Python3.14라 truststore 0.10.4 SSL verify_mode 무한재귀로 온라인 pip 전부 RecursionError → mutagen을 Linux 샌드박스서 받은 `mutagen-1.47.0-py3-none-any.whl`(범용)로 `--no-index` 로컬설치 우회(`_mutagen_whl/`). 근본해결(런타임 Py3.12/13 재생성 or truststore 교체)=종민 결정 대기.
- 2026-06-18: **J단원 — 조회수/리텐션 개선 6종 집필규칙 박음 (종민: 전부 반영·퀄리티 유지).** 결정=KPI 균형·길이 25~30초·하이브리드 엔딩. 반영(전부 `article_authoring_spec.md`, 렌더코드 무수정=오디오 스팅 결합 보존): ①길이 25~30초(본문 합계 ≈180자·문장 ≤30자·팩트 3개) ②1영상1주장 ③cold-open(hook 헤드라인 숫자/가격 시작) ④검색질의형/질문형 제목 ⑤시리즈 고정코너 prefix ⑥하이브리드 루프 엔딩(CTA카드 유지+마지막 줄 오프닝 루프백). **왜 코드 안 고침**: OPENING_SEC(2.0)·OUTRO(3.2)는 opening_sting/cta_sting mp3(gitignore, 렌더PC)와 타이밍 결합 → 블라인드 변경 시 오디오 겹침 = 퀄저하. 렌더타이밍 추가단축은 스팅 재컷+렌더PC 시각검증 필요한 별도 작업. **최고 ROI는 유지곡선 데이터**(미보유)로 어느 초에 이탈하는지 확인.
- 2026-06-18: **concept_scout 개념발굴 = 개별 파일 유지 + '하나씩 따로 생성' 안내 + 중복블록 버그 수정 (E단원, 종민).** 1차로 '한 장 격자 통합'을 시도했으나 **종민 지적=cpt_*.png 개별 파일이라야 청크 1:1 매핑됨** → 철회. 최종: `codex_concept_scout.py` 블록빌더는 개념마다 별도 ```text``` 블록 유지(STYLE #3='개별 파일로 따로' 원복), 섹션 상단에 **GPT(이미지 생성기) 대상 지시문** 추가(req["prompt"] 밖, 종민 "GPT가 개별 생성하게 유도하는 프롬프트"): '아래 개념들을 하나씩 각각 별도 이미지로 생성, 총 N개=N장, 격자(grid)·콜라주·분할·여러 칸 금지, 한 이미지=한 개념, 블록 제목 cpt_*.png로 저장'. count-aware(len(requests)). + START..END 중복블록 누적 버그 수정(dedup을 `re.sub`로 전부 제거 — 종민 출력에 2번 박히던 것). **함정(I단원 재확인)**: 이 편집을 Edit 도구로 했더니 21.6KB(<26KB)인데도 파일 꼬리(render_md+main) truncate(git diff 44 del) → HEAD 복원+bash-python으로만 재적용. **근본**: 개념 품질 자체는 engine=lexical-fallback(임베딩 모델 미설치)이라 키워드 조각 = 부실 → CLIP/임베딩 살려야 개선(폴백 시 개념발굴 억제 옵션은 종민 결정 대기).
- 2026-06-18 (버그픽스): **문의접수 카톡 리포트 날짜 1일 밀림 (G단원).** `updateKakaoInquiryCoverage`가 날짜를 `new Date(ymd+'T00:00:00+09:00')`(KST 자정 instant)로 써서, **스프레드시트 파일 시간대가 Asia/Seoul이 아니면** 표시 시 전날로 당겨짐(03-09 입력→03-08 표시 = 친구수/JKL보다 1행 위로 보임). 스크립트 tz는 서울이나 시트(파일) tz가 달랐던 게 근본. 수정: `Code.js:769` `ssTz=SpreadsheetApp.getActive().getSpreadsheetTimeZone()` + `:822` `Utilities.parseDate(ymd, ssTz, 'yyyy-MM-dd')`(시트 tz 자정=표시 동일, tz 무관 안전). 배포 후 📉 문의접수 입력률 갱신 1회 재실행 시 옛 행도 정정(normalizeYmd_는 KST 일관 → parseDate sheetTz). 시트 tz 자체 변경은 TODAY()·타 수식 영향이라 코드로 처리. node --check PASS.
- 2026-06-19: **길이 목표 25~30초 → 30초 안팎(최대 35초)로 완화 (J단원, 종민).** 25초는 내용이 엉성해져 비채택. 본문 합계 180→220자·팩트 3개→3~4개·문장 ≤30→≤32자. 56초처럼 늘어지는 것만 금지. 정본 `article_authoring_spec.md`.
- 2026-06-19: **C단원 — CasualHeader 슬림(116→88) + 경쟁채널(싸당) 벤치마크·실영상 UI평가 박음.** 오프닝 헤드라인 상단 OK(문구가 약함)·비주얼 여백은 contain/아트워크라 CSS 단순조정 아님·진짜 문제는 약한 그림(CLIP 폴백). 우선순위=길이>훅>그림품질>UI. 노출0=콜드스타트(브레이크아웃 필요).
- 2026-06-19 (버그픽스 보정): 위 카톡 날짜 fix의 `Utilities.parseDate(ymd, ssTz, ...)`가 런타임 "timeZone String 형식" 에러(getSpreadsheetTimeZone 비정상). → **`new Date(ymd + 'T12:00:00Z')`(정오 UTC)**로 교체 = tz 인자 불필요, UTC-12~+11 모든 시간대에서 같은 날짜 표시. ssTz 줄 제거. node --check PASS.
- 2026-06-19 (사장님 결정): **문의접수 입력률 갱신 기능 비활성화 (G단원).** 종민이 문의접수를 A:E(수기) + H:K(카톡 원본: 날짜/친구수/채널추가/채팅요청)만으로 운영키로 결정 → L:Q 자동계산 불필요. `Code.js` onOpen 메뉴 `📉 문의접수 입력률 갱신` + refreshAll의 `updateKakaoInquiryCoverage(false)` 호출 제거(함수 정의는 dead로 잔존, 원하면 추후 full purge). 날짜 tz 버그도 함수 미실행으로 자동 소멸. node --check PASS.
- 2026-06-19 (구글 맵핑, 종민 요청): **구글 GA4 매칭 추가 (G단원, 당근 패턴 복제).** 신설 `apps_script/google-sync.js`: `createGoogleIntegratedSheet`(구글_통합 20컬럼=당근_통합 동일) / `syncGoogleGA4`(GA4 source="google" 리터럴, `FILTER(UTM_KEYVAL, UTM_CH="구글")`, 문의접수 D="구글" 카톡문의, **Script Property 불필요** — 당근 DANGGN_UTM_SOURCE 대응 없음) / `showUnmappedGoogleAdgroups`(UTM_매핑 채널=구글 미매핑 표시) / `setupGoogleTrigger`(매일 02:35) / 메뉴 🔵 구글 자동화. Code.js onOpen `buildGoogleSyncMenu_` + refreshAll `syncGoogleGA4({interactive:false})` 추가. **matrix는 raw '구글' 시트 유지**(당근과 동일 — 구글_통합은 per-캠페인 granular 뷰, 매트릭스 변경 위험 회피). GA4 google utm_campaign 실측(혼재): 디스플레이_리틀리(162)/price_check(45)/디스플레이_리틀리_무료폰(30)/free_phone(7)/kids 등 — 한글 캠페인명+영문 슬러그. node --check PASS, 전 .js 회귀 PASS. **셋업**: 🆕 시트신설 → 구글_통합 A~F(날짜/캠페인/광고그룹/노출/클릭/지출) 수기 → UTM_매핑 채널=구글 행(광고그룹명→utm_campaign, STEP1 🏷️ 드롭다운 갱신하면 GA4 실측값 선택 가능) → 🔄 GA4 매칭 → ⏰ 02:35 트리거. push = google-sync.js + Code.js.
- 2026-06-19 (UI): **채널 메뉴명 단축 (종민 요청, 메뉴바 너무 김).** createMenu 제목에서 ' 자동화' 제거 — 📘메타/🎥유튜브/🟢네이버/🟠당근/🔵구글 (meta-sync·youtube_sync·naver-synce·danggn-sync·google-sync 각 1곳). 일부 alert/log 텍스트의 '...자동화' 참조는 메뉴바 아님(이모지 동일해 탐색 영향 없음, 추후 정리 가능). node --check 5파일 PASS.
- 2026-06-19: **영상 설명란 빈 채로 생성되는 버그 수정 (C단원, 종민 제보).** publish_codex_package.py가 `output/<slug>/captions.md`에서만 캡션을 읽어, 카드뉴스 렌더를 안 거치는 **영상-only 슬러그(028 등)는 그 파일이 없어 YT설명·Reels·TikTok 본문 전부 공백**(제목·태그는 정상). 수정=`article_captions()`로 기사 JSON captions_md 폴백(output 비면). 검증: 028 폴백 시 YT 567자·IG 402자·TikTok 183자 채워짐. 재생성=`python scripts/publish_codex_package.py "<영상>" <slug> <date>` 또는 재렌더.
- 2026-06-19: **사전승낙서·리틀리 링크 = 캡션 토큰 치환으로 박음 (C단원, 종민).** caption_template.md·기사 47개가 `{LITTLY}`·`{PRECON_URL}` 플레이스홀더를 쓰는데 publish가 치환을 안 해 리터럴로 출력되던 것 → `publish_codex_package.apply_link_tokens()`(captions 로드 직후) 추가: `{LITTLY}`→litt.ly/phonespot, `{PRECON_URL}`→ictmarket precon URL. YT/IG/TikTok 각 채널 1회씩 실제 URL. (URL 상수 LITTLY_URL·PRECON_URL = 정본, 바뀌면 여기만 수정.) 1차로 시도한 고정 footer는 템플릿의 ▶폰스팟광교점/사전승낙서 블록과 중복이라 철회.
- 2026-06-19: **브랜딩 광교점 → 휴대폰성지 폰스팟(전국 온라인) 전환 (C·B단원, 종민).** 카톡 핸들 `@폰스팟광교점`→`@휴대폰성지폰스팟`, CTA 브랜드 `폰스팟 광교점`→`휴대폰성지 폰스팟`, CTA 위치 `광교호수공원 B1-47`→`내 손 안의 성지찾기, 폰스팟`, 오프닝 키커 `광교 미니 IT 브리핑`→`휴대폰성지 IT 브리핑`. **코드 기본값**: `CasualCta.tsx`·`build_script.py`(L250-251,271-272)·`auto_polish.py`(L297-298,318-319)·`Cover.tsx`. **템플릿**: caption_template.md(14건)·article_authoring_spec.md(2건) — 브랜드/카톡 문구만, **주소(광교호수공원로 20 B1-47호)·사전승낙서 = 법적이라 보존**. 범위=템플릿+코드+신규기사(**기존 48개 기사 captions_md는 미변경**=과거건). 이미 빌드된 슬러그(028 등)는 shorts_script.json에 옛 kakao/location이 박혀 재렌더해도 안 바뀜 — **재빌드해야** 신규 브랜드 반영. 함정: location 문구가 길어져 CTA 카드서 줄바꿈 가능(렌더PC 확인).

- 2026-06-19 (구글 Ads API): `apps_script/google-ads-sync.js` 신설. refresh_token→access_token→searchStream(GAQL v23, FROM ad_group, segments.date BETWEEN 최근N일) → 구글_통합 D/E/F(노출/클릭/지출) upsert(키=날짜|광고그룹명) → syncGoogleGA4 후속 호출(G~P 수식). Script Property 6개: GOOGLE_ADS_DEVELOPER_TOKEN/CLIENT_ID/CLIENT_SECRET/REFRESH_TOKEN/LOGIN_CUSTOMER_ID(MCC)/CUSTOMER_ID. cost_micros/1e6=원. 메뉴 🔵 구글에 📥 Ads API 수집(7일)/백필(30일)/🔑 연결테스트/⏰ Ads Trigger(02:25) 추가(google-sync.js buildGoogleSyncMenu_). 함정: CUSTOMER_ID가 MCC(LOGIN_CUSTOMER_ID) 아래 미연결이면 USER_PERMISSION_DENIED. v 종료 시 GADS_API_VERSION 상수만 갱신(v19=2026-02 종료).

- 2026-06-19 (구글 Ads API 신청/대기): Basic 액세스 신청 제출(MCC 3964705146, 설계문서 ads/PhoneSpot_GoogleAdsAPI_DesignDoc.pdf). 승인대기 ~3영업일. 코드(google-ads-sync.js)·계정연동 완성, Test등급이라 운영계정 차단 = DEVELOPER_TOKEN_NOT_APPROVED. 운영가이드+재개절차+함정(MCC/CUSTOMER 반대저장 주의, login-customer-id 비우면 통과) = ads/GOOGLE_ADS_API.md. 승인 전까지 D/E/F 수기.

- 2026-06-22 (대시보드 3일 + 브리핑 상세화 + 알림 정리):
  · 통합대시보드 기간 드롭다운 3곳(E16/E28/E36)에 "최근 3일" 추가 + N16/N28/N36 시작일 수식에 TODAY()-2 분기. KPI 상세표(updateKPISummary)에 "최근 3일" 행 추가(어제 다음, 클리어범위 A9:I14->A9:I15, periods 5행=어제/3일/7일/14일/30일). ★ 코드 배포만으론 시트 안 바뀜 — updateChannelMatrixWithGA4/updateKPISummary 실행(전체새로고침)해야 드롭다운/표 재도색됨.
  · GA4 원본 자동수집: refreshAll에 fetchGA4Daily() 추가(맨 앞). ★ 단 refreshAll 트리거는 최종실행 "-"(안 돎) — 실제 GA4 일일수집은 Apps Script UI에 fetchGA4Daily 시간트리거(오전1~2시, 매칭 2:13~2:35보다 앞) 직접 추가로 해결. GA4_자동이 20일에 멈춘 원인=fetchGA4Daily 트리거 부재(수동 실행 때만 채워졌음). 밀린 날짜는 메뉴 "GA4 30일 백필"로 보충.
  · 텔레그램 정리(alerts.js): 목표경고(checkAdTargets_)·헬스체크(runHealthCheck_) 자동발송 전부 제거(sendMorningBriefing + refreshAll에서 호출 삭제, 메뉴 수동버튼만 잔존). 아침브리핑(09:00) 상세화 = [기간별 종합] KPI표 A11:I15 라벨기준(어제/3일/7일/14일/30일 광고비·문의·확인·개통·CPL) + [어제 채널별] 메타(F/G/H)·네이버(F/G/H)·당근(D/E/F)·구글(D/E/F) 노출/클릭/지출 합산. 라벨기준이라 3일행 유무 자동대응.
  · 함정: 브리핑 [기간별 종합]은 KPI표를 읽으므로, KPI표가 구 레이아웃이면 3일 누락 → updateKPISummary 1회 실행 필요. 채널 노출/클릭/지출 컬럼맵=메타/네이버 6/7/8, 당근/구글 4/5/6(1-based).

- 2026-06-22 (토큰알림 + 야간대시보드 트리거):
  · D) alerts.js checkTokensDaily() — 메타(/me)·구글Ads refresh_token(교환시도)·네이버키·텔레그램 점검, 문제시만 텔레그램 경고. 메뉴 🔔에 "토큰 점검 지금/트리거(08:30)". 인수인계 핵심(토큰 죽으면 폰 경고).
  · E) refreshAll 트리거 최종실행 "-" 원인 = 13개 순차로 6분 초과 추정. 대체 = Code.js nightlyDashboard()(대시보드 재빌드만, API 호출 없음, 빠름) + setupNightlyDashboardTrigger()(매일 03:00). 데이터 sync는 개별 트리거가 담당, KPI표는 라이브 수식이라 자동. 기존 refreshAll 트리거는 UI에서 삭제 권장. UI alert는 트리거에서 throw하므로 각 호출 try로 감쌈.
  · B) UTM 자동매핑 = 미구현 결정(detection은 이미 autoDiscoverAdsets_/autoDiscoverNaverAdgroups_ 존재, utm_campaign 영문슬러그는 사람 판단 필수).

- 2026-06-22 (광고그룹 추이 개선): adgroup-trend.js — ① CPL 컬럼(I열, =지출/문의수) 추가(데이터표 9컬럼). ② 차트 우축을 CPC→CPL로 교체(CTR·문의율 좌축
- 2026-06-22 (광고그룹 추이 개선): adgroup-trend.js — (1) CPL 컬럼(I열, =지출/문의수) 추가(데이터표 9컬럼). (2) 차트 우축을 CPC→CPL로 교체(CTR·문의율 좌축%, CPL 우축원, CPC는 표에만=스케일충돌 회피). (3) onEdit 단순트리거 추가 = 통합대시보드 B61(채널)/E61(광고그룹)/H61(기간) 편집 시 자동 refreshAdgroupTrendChart(메뉴 수동클릭 불필요, 불편 해소). 적용: 콘솔 반영 후 "차트 셋업(1회)" 재실행으로 헤더(CPL 라벨)·차트 재도색.

- 2026-06-22 (대시보드 깨짐 수정): 통합대시보드 옛 "월별 카톡표"(45~57행)는 갱신 함수 없는 잔여물인데 recordLastRefresh_가 A46(2월 라벨 자리)에 업데이트 시각을 써서 깨져 보임. 수정 = recordLastRefresh_가 A45:H58 정리(clearContent+Format) 후 시각을 A59에 기록(어떤 표와도 비충돌). 잔여표는 사장님 결정으로 삭제. 적용 = nightlyDashboard 1회 실행(끝에서 recordLastRefresh_ 호출).

- 2026-06-22 (버그 일괄 수정): (1) ★logSync_ 중복 정의(meta 2인자 vs danggn 3인자) — meta가 나중로드로 이겨서 3인자 호출 시 실패를 ✅성공으로 기록+메시지 유실. → meta-sync.js logSync_를 2·3인자 모두 처리하게 통합, danggn 중복 제거. (2) listAllAdgroups 중복(naver vs test.js) → test.js 함수명 listAllAdgroups_test_로 변경. (3) 파일간 중복 const/var 없음 확인(있으면 V8 전체 에러). (4) 광고그룹추이 자동갱신 = 설치형 onEdit 트리거(setupAdgroupEditTrigger, 메뉴 "⚡ 토글 자동갱신 켜기"). onEdit(e)→onEditAdgroupAuto_로 개명. (5) 대시보드 여백: recordLastRefresh_가 41~59행 숨김(hideRows)+옛 시각/잔재 정리, 업데이트 시각을 상단 A7로 이동. 적용=nightlyDashboard 1회.

- 2026-06-22 (락 영구해결 + 주간리포트): (1) ★index.lock 근본차단 — 자동커밋 codex_github_upload.py main()에 clear_stale_lock() 추가(60초↑ 묵은 락=crash잔재 제거, 활성<60초는 보존). 이게 "커밋이 락에 막혀 배포 안 됨"의 근원이었음. STEP7 위생 연동. (2) 주간 성과 리포트 alerts.js sendWeeklyReport() — 지난 7일(어제까지) 채널별 광고비(메타/네이버 H, 당근/구글 F)+문의(문의접수 A 카운트)+CPL 텔레그램. setupWeeklyReportTrigger 매주 월 09:10. 메뉴 🔔에 추가. (3) GitHub Actions deploy-apps-script.yml에 배포 성공 텔레그램 알림 스텝 추가(2026-06-22, github Secrets TELEGRAM_BOT_TOKEN/CHAT_ID).
