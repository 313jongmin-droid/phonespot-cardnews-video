# 패널 엔진 task — 진입 가이드 (control plane)

> **이 task = 패널/오케스트레이션만.** 영상 콘텐츠·렌더 내부는 안 만진다(제작 task = `shorts/RENDER_TASK.md`).
> 주제엔진(`_docs/TOPIC_ENGINE.md`·`shorts/promo/TOPIC_TO_PROMO.md`)은 **별도 "주제 task" 소유 — 여기서 편집 금지.**
> 상위 구조: `CLAUDE.md`(헤드) → `_docs/SYSTEM_MAP.md` 대단원 **A(패널)** → 이 파일.

## 1. 소유 (이 task가 만지는 것)
- `CODEX_VIDEO_DESK/dashboard/server.py` — 패널 본체. `INDEX_HTML`(UI+JS) + 액션 디스패치(`if action == "..."`) + `PANEL_VERSION`(SSOT).
- `CODEX_VIDEO_DESK/dashboard/` — `start_hidden.ps1`(버전게이트), `remote_queue.py`(렌더 잡 큐), `auto_update.cmd`, `stop_panel.ps1`.
- `CODEX_VIDEO_DESK/RENDER_WORKER/worker.py` — 잡 클레임 → `commands_for`(액션→bat) → `result_after`(결과 탐지) → 업로드.
- 큐/상태: `remote_queue`(렌더 잡), `_state/style_requests.jsonl`(스타일 요청 큐: `style_request`/`style_pending`).
- 패널 bats: `00_PHONE_SPOT_PANEL.bat`, `01_START_RENDER_WORKER.bat`, `작업표시줄에_패널_고정.bat`, `수신PC_자동업데이트_*.bat`.
- 화면 골격(v40): 헤더 → 가운데 트랙세그먼트(카드뉴스·영상/타이포/실사AI) → WORK(트랙별) → `#commonMonitor`(공용). `switchTrack`.

## 2. 안 만지는 것 (제작 task 영역)
- `shorts/src/*`(Remotion 컴포넌트), `shorts/scripts/build_*.py`, `run_*.bat` **내부 로직**, `promo/`·`promo_ai/` 콘텐츠, `cardnews/` 기사·이미지·렌더.
- 패널은 이것들을 **호출만** 한다(수정 ❌).

## 3. 인터페이스 계약 (P → R)
- 렌더 트리거: 액션 → `REMOTE_QUEUE.enqueue(action, slug, ...)` → worker `commands_for`가 **`run_<track>.bat <인자>`** 실행.
- 결과 탐지: worker `result_after`가 **`CODEX_VIDEO_DESK/RESULTS/<폴더명에 slug 포함>/*.mp4`** 를 찾음. → 제작 bat은 결과를 이 규칙으로 떨궈야 함(예 `run_promo.bat`이 `RESULTS/{NN}_{label}_{preset}_promo/`).
- 스타일 요청: 패널이 `_state/style_requests.jsonl`에 `{slug,track,status:pending}` append. **작성은 Claude(주제/제작), 패널은 트리거만.**
- 기존 계약 사례: `shorts/promo/PANEL_INTEGRATION_HANDOFF.md`(promo). 새 트랙도 이 패턴.

## 4. 함정 / 규칙
- `server.py` 165KB·`SYSTEM_MAP`·`CLAUDE.md` 대형 = **bash-python 편집만**(Edit툴 truncation), 태그 균형(section/div/script) + `PANEL_VERSION` bump 검증(I단원).
- 화면 안 바뀌면 `PANEL_VERSION`만 올림(ps1이 읽음).
- 샌드박스 렌더 불가 → 동작 검증은 렌더PC 로그.

## 5. 시작 명령
`CODEX_VIDEO_DESK/PANEL_TASK.md 읽고 패널(dashboard/server.py·worker·큐)만. 콘텐츠/Remotion 안 건드림.`
