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
- 컴포지션 정의: `shorts/src/Root.tsx`(NewsroomShort/CasualShort/Promo-*/**Cover**, 전부 1080×1920).

**SNS 품질 — 후킹·레이아웃·오디오·닫기 (2026-06-13, 021 품질점검발, 재렌더 검증)**
- **오프닝 후킹**: `shorts/src/components/OpeningHook.tsx` — 검정 → **다크 그라데이션 + 움직이는 주황 글로우 + 주황 키커 pill(채널 태그라인) + 빠른 큰 헤드라인**. `Root.tsx` `OPENING_SEC` 1.5→1.1→**2.0**(후킹 읽을 시간 확보).
- **닫기 CTA 디자인 카드**: `shorts/src/components/casual/CasualCta.tsx`(신설) — 일러스트 폐기, 오프닝과 같은 결(다크+주황글로우+키커 "폰스팟 광교점" + "휴대폰 구매할 땐?" + 주황 펀치 + 연락처 박스 kakao/location/litt). `Composition.tsx` casual cta 분기를 `CasualCard type=cta` → **`CasualCta`** 로 교체(데이터=`script.cta`, audioKey=cta). newsroom은 기존 `CtaCard` 유지.
- **아웃트로 +2초**: `Root.tsx` `OUTRO_SEC` 1.2→**3.2**(끝화면 = `ChannelOutro` 로고+구독 더 길게).
- **카드 전환 애니메이션**: `CasualCard.tsx` `cardEnter`(frame 0~7 페이드+슬라이드업)를 비주얼 컨테이너에 적용 → 하드컷 완화(일러스트 포함 전 카드).
- **제목바 중복 제거**: `shorts/src/components/casual/CasualCard.tsx` — `CasualTitleBar`를 **`type==="hook"`일 때만** 렌더(본문 4개 카드 반복 제거 + 비주얼 영역 확대). 맥락은 오프닝+헤더+비주얼/자막으로 충분.
- **자막 세이프영역**: 점검 결과 자막은 화면 **중하단**(아래 ~700px 흰 여백)이라 플랫폼 UI 안 가림 → 변경 안 함(`CasualCaption` height 840, padding-top 128).
- **라우드니스 −14 LUFS**: `shorts/scripts/finalize_sns_video.py` `common_prefix`에 `-af loudnorm=I=-14:TP=-1.5:LRA=11`(나레이션 −16.5가 작던 문제). env `PHONESPOT_TARGET_LUFS`(기본 -14, `off`로 끔).
- **BGM**: 캐주얼 트랙 현재 나레이션만(무음구간 多) — BGM 추가는 보류(음악풀+Composition 믹싱 필요).
- **길이 목표**: 35~45초(56초는 길다). 레버는 코드가 아니라 **기사 집필**(J단원 `article_authoring_spec.md`: 카드 본문 문장 ≤35자·6카드 ≈250자).
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
  - **매칭 경로**(`semantic_match` 청크 루프): ① 소스 카드이미지(prompt.md 설명 임베딩) ② 라이브러리 일러스트 텍스트/태그 임베딩(`best_ill ≥ EMBED_MIN_ILLUST`) ③ 소스/마스코트 유지 ④ 그림내용(CLIP) 매칭 ⑤ 중립 필러(`pick_neutral`). 엔진 없으면 lexical 임계(`MIN_*_SCORE`).
  - **상수(전부 env 오버라이드)**: `EMBED_MIN_IMAGE`(0.42)·`EMBED_MIN_ILLUST`(**0.48**, 0.42는 너무 관대해 먼 그림 통과)·`EMBED_MIN_ILLUST_IMG`(0.28, CLIP 내용)·`NEUTRAL_FILLERS`(★ 진짜 중립 phone/device만 — newspaper/shield/microphone/meeting_room/forecast는 "특정 의미"라 제외)·`ILLUST_BLOCKLIST`(기본 비움, env 비상용)·`EXCLUDE_UNVERIFIED_CONCEPT`(기본 True).
  - **★ 범용 오배치 방지 3종 (2026-06-13, SNS 품질점검 후)**:
    1. **중립 폴백 정상화**: 매칭 실패 시 의미 있는 그림(방패/신문/마이크) 대신 phone/device 일반 그림.
    2. **content-gate(CLIP)**: 텍스트로 고른 일러스트도 실제 그림이 주제와 맞는지 `EMBED_MIN_ILLUST_IMG`로 검증. **단 CLIP 그림엔진(`codex_image_embed`/`image_embed_cache.json`)이 설치돼야 작동** — 없으면 무력(빈 데이터→통과).
    3. **미검증 개념아트 정책(`_is_unverified_concept`)**: `cpt_*`(개념요청 텍스트로 자동생성, 그림 미검증)는 **텍스트매칭에서 제외**(CLIP 켜지면 content 경로로만 검증 사용). 이름 하드코딩 대신 카테고리 규칙 — cpt_496029c6(=AI개념인데 보이스피싱 그림) 같은 케이스 일괄 차단. 읽기이름 일러스트는 영향 없음.
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
- Gemini 키 없으면 readable 이름 폴백(cpt_) — 에러 아님. **단 cpt_는 그림 미검증이라 텍스트매칭 제외(위 정책 3)**.
- **★ CLIP 그림엔진(`codex_image_embed`)이 PC에 미설치면 content-gate 무력** → 텍스트/태그 매칭만으로 동작. 즉 "이름↔그림 불일치"의 범용 차단은 **CLIP 켜야 완전**. 안 켜진 동안은 정책 3(cpt_ 제외)+중립폴백+임계 0.48이 방어선. 검증 단서: `shorts/codex/image_embed_cache.json` 존재 여부.
- **잘못 그려진 정식(비-cpt_) 일러스트**(예: ti_decrease=티타늄'감소'를 슬림화에 사용)는 특정 이름 하드코딩 ❌(원칙). 해결=그 그림을 더 중립/정확한 것으로 교체하거나 CLIP content-gate 활성화.
- **수정 작업법**: 이 파일은 Edit 누적이 꼬리를 truncate한 적 있음(2026-06-13) → 큰 변경은 **bash-python(assert count==1 + py_compile + tail 확인)**, 깨지면 `git show HEAD:<path>`의 꼬리로 복구.

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
- **★ 미커밋(untracked) 기사 JSON 유실 사고 (2026-06-13)**: `git stash --include-untracked`(pull 전 단계)는 **추적 안 된 파일을 working tree에서 stash로 쓸어담는다.** 다른 task가 `cardnews/articles/NNN_*.json`을 만들고 **커밋 전**일 때 auto-update/pull bat이 돌면 그 기사가 사라져 "article not found" → 준비/렌더 exit 1. **데이터는 stash에 보존**되어 복구 가능: `git ls-tree -r --name-only "stash@{0}^3"`로 확인 → `git show "stash@{0}^3:<path>" > <path>`로 개별 복원(통째 pop 금지).
  - **근본 원인**: **노트북(개발기)에 auto-update 마커(`CODEX_VIDEO_DESK/TEMP/panel/auto_update.on`)가 켜져 있으면** 패널 켤 때마다 stash가 돈다. 노트북=push only(STEP 0)이므로 **마커 꺼야 함**(`수신PC_자동업데이트_끄기.bat` 또는 마커 삭제). 러너(부사수/사무실)는 켜둠이 정상.
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
- **★ 영상 길이 목표(2026-06-13)**: 35~45초(SNS 리텐션). 길이는 narration/카드 본문 글자수가 좌우 → **카드 본문 기본 1~2문장·한 문장 ≤35자·6카드 합계 ≈250자**, 군더더기("~전망됩니다" 반복) 줄이기. 사실 못 담으면 팩트 3개로. (스펙 §body 규칙에 박힘)
- **★ 후킹 공식(2026-06-13)**: 오프닝/인트로 첫 문장 + cards[0] = 설명형 ❌ → **호기심 갭/긴장형 5패턴**(질문·반전·손해회피·숫자단정·대상지목). 결론/궁금증 먼저, 과장·낚시 금지. (스펙 narration_md §후킹 공식에 박힘)

**함정**
- 기사 JSON은 git 추적 = 중복방지 DB. 새 주제는 `cardnews/articles/*.json` 중복 회피 먼저.
- **길이=코드로 못 줄임**(나레이션 TTS 길이 좌우). 56초처럼 길면 집필 단계에서 줄여야 함.

---

## 변경 이력 (이 맵 자체)
- 2026-06-13: **고퀄 batch 박음 (재렌더 181856 검증).** C단원: 오프닝 2.0초·아웃트로 3.2초(+2)·**닫기 CTA 디자인카드 `CasualCta`(일러스트 폐기)**·카드 전환 애니메이션(`cardEnter`). J단원: 후킹 공식 5패턴. (1 CLIP·9 제품이미지는 제외/대기.)
- 2026-06-13: **C단원 SNS 레이아웃·오디오 + J단원 길이목표 박음 (P2·P3).** 제목바 hook-only(`CasualCard.tsx`), 자막 세이프영역 안전(변경X), 라우드니스 −14(`finalize_sns_video.py` loudnorm, env off), BGM 보류. 길이 35~45초 목표 = 기사 집필 레버(`article_authoring_spec.md` §body + J단원). 검증=실행PC 재렌더.
- 2026-06-13: **E단원 의미매칭 범용수정 + C단원 후킹 박음 (SNS 품질점검발).** 중립폴백 정상화·EMBED_MIN_ILLUST 0.48·content-gate(CLIP 미설치면 무력)·미검증 cpt_ 텍스트매칭 제외(`_is_unverified_concept`, 카테고리 규칙·env). 함정에 CLIP 의존성·비-cpt 오배치는 데이터교체 박음. C단원 후킹=`OpeningHook.tsx`(다크+주황글로우+키커 pill, OPENING_SEC 1.5→1.1).
- 2026-06-13: **A단원 패널 UI 단계적 노출 박음(v31~v32)** — 영상작업 보조버튼 2묶음을 공통 `.foldbar` 접기 토글(보기·편집 + 라이브러리·시스템 관리, 둘 다 기본 접힘·동일 UI·캐럿)로 → 첫 화면에 상태+로그 노출. 보기·편집은 `localStorage panel.viewEdit` 기억. 런타임 4박스 슬림. PANEL_VERSION v30→v32.
- 2026-06-13: **A단원에 패널 iOS 디자인 시스템 박음(v25~v30)** — 토큰/Pretendard/legacy alias/풀폭 거터/sticky 좌측리스트/우측 페어(상태\|로그·기록\|결과)/2줄 슬러그행(idx+1)/상단 흰카드+컬러점/그림자 단일화. 함정에 **Edit 누적 truncation 실사고 + bash-python 작업법 + 복구법** 박음. 롤백=`server.py.bak_pre_ios_20260613`.
- 2026-06-13: **F단원 함정에 미커밋 기사 유실 사고 박음** — auto-update `stash --include-untracked`가 untracked 기사를 쓸어감(노트북 마커 ON이 원인). 복구법(`stash@{0}^3`) + 재발방지(노트북 마커 OFF + pull bat `auto_update.cmd`/`부사수PC_원클릭_셋업.bat`에 기사 자동커밋 박음).
- 2026-06-13: **B 단원 인사이트 누적 학습 + 가중치 라벨 매트릭스 박음.** 마스터 룰 문서에 `_docs/INSIGHTS_LOOP.md`(시트 직접 Read 단일 모델 — 코덱스·GitHub·Drive MD·mklink 폐기) + `cardnews/templates/caption_template.md`(5채널+영상 나레이션) 명시. 가중치 라벨 6종(yt+30/yt-hook+20/meta+20·30/store-active+30/season+30/freshness+10/dup-100) 정본 위치 = `INSIGHTS_LOOP.md` §3. 함정에 "시트 운영 메모 7일 스캔 빼먹으면 매장 핵심 캠페인 누락(예: 삼성 페스티벌)" 박음. H 단원 outbox 파일명 표준(`<YYYY-MM-DD>_collect*.txt` 후보표 / `<NNN>_ready.txt` 작성 완료 통지) + listener 함정(부팅 자동시작·송신 검증) 박음.
- 2026-06-13: **C단원에 커버(9:16 표지) 기능 박음** — `Cover.tsx`(CoverShort) + `Root.tsx` id=Cover + `render_cover.mjs`(renderStill, 번들캐시 재사용) + `run_codex_casual.bat` Step6 직후 best-effort. 결과 = `RESULTDIR\<RESULTKEY>_cover.jpg`. Remotion 4.0.404.
- 2026-06-13: **문서화 규약 박음** — "가이드 박아"는 이 3층 구조(헤드→SYSTEM_MAP 대단원→마스터 가이드)에 합류시키는 것이지 1회성 요약본 생성이 아님. 절차 정본 = CLAUDE.md "문서화 규약" 절. 헤드+이 파일 상단에 동시 명시.
- 2026-06-13: 신설. 이번 세션 git-bat 탐색 수정(F 단원: GitHub Desktop 내장 git을 `for /d`로 탐색, `dir app-*` 패턴 금지) + 런타임파일 git 비추적 + 인코딩 규칙(I)을 대단원으로 정리. CLAUDE.md STEP 1에 "수정 작업 인덱스"로 등록.
- 2026-06-12 (세션2 합류): 대단원 G에 광고 생성기 대개편 핵심+함정 박음 — 8행 변주엔진·1:1매핑·이미지배너+랜덤아트·지역/컨셉 무조건반영·길이/타겟 실반영·Gemini 의미매칭(`getSemanticAdMatches`)·슬로건→이미지(`copyImageWithHeadline`). 정본 상세 = IMPLEMENTATION_GUIDE §0-1, 변경이력 = CLAUDE.md STEP8.
- 2026-06-11 (광고운영 task 합류): 대단원 G에 6/11 세션 블록 박음 — 통합대시보드 자동 합산 패치(`Code.gs` `updateChannelMatrixWithGA4`+`updateKPISummary`+`addTimeSeriesChart` 시트 매핑 분리), 인스타/네이버 자동화 완료, `generateMetaInsightsMarkdown` 누락 사고 + 복구, 카카오톡 채널 불가/스레드 보류 확정, SNS 자동화 매트릭스(`ads/SNS_AUTOMATION_ROADMAP.md`) 신설, 멀티 브랜드 모노레포 제안(`ads/MULTI_BRAND_ARCHITECTURE.md` 신설 — Phase 1 다른 task `generator.html` 종료 후 시작). 정본 = `ads/META_AUTOMATION.md`·`NAVER_AUTOMATION.md`·`SNS_AUTOMATION_ROADMAP.md`·`INSTAGRAM_AUTOMATION_PENDING.md`·`MULTI_BRAND_ARCHITECTURE.md`. CLAUDE.md STEP 1·2·4·8 동기화.
- 2026-06-11 (Phase 1 셋업 완료 16:00 KST): G 단원에 셋업 결과 박음 — 로컬 `apps_script/` clasp clone + GitHub repo `313jongmin-droid/phonespot-cardnews-video` + Actions workflow + Secrets. `clasp push --force` 자동 배포 27초 검증. **함정 핵심: CLASP_JSON Secret은 한 줄 압축 JSON 필수**(multiline은 `JSON5: invalid character 'P' at 12:1` 에러). 정본 = `ads/MULTI_BRAND_ARCHITECTURE.md` "Phase 1 셋업 완료" 섹션.
