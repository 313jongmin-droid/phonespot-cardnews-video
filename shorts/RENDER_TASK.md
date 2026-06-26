# 영상 제작 task — 진입 가이드 (production plane)

> **이 task = 카드뉴스·영상 콘텐츠 작성 + 렌더만.** 패널/서버 UI는 안 만진다(패널 task = `CODEX_VIDEO_DESK/PANEL_TASK.md`).
> 주제엔진(`_docs/TOPIC_ENGINE.md`·`shorts/promo/TOPIC_TO_PROMO.md`)은 **별도 "주제 task" 소유 — 여기서 편집 금지.**
> 상위 구조: `CLAUDE.md`(헤드) → `_docs/SYSTEM_MAP.md` 대단원 **B(카드뉴스)·C(영상)** → 이 파일 + 트랙별 정본.

## 1. 소유 (이 task가 만지는 것)
- `shorts/src/*` — Remotion 컴포넌트(`Root.tsx`·Casual·Newsroom·Promo·Cover).
- `shorts/scripts/build_*.py`·`promo_*.py`, `shorts/run_*.bat`(렌더 엔트리), `shorts/public/`(assets·sfx·music·fonts).
- `shorts/promo/`(타이포 콘텐츠·스타일·MD), `shorts/promo_ai/`(실사 Higgsfield).
- `cardnews/` — `articles/`(기사 JSON)·`images/`·`output/`·`scripts/`·`templates/`(authoring 스펙).
- 콘텐츠 작성: 기사 JSON, promo MD, 실사 프롬프트(품질=Claude).

## 2. 안 만지는 것 (패널 task 영역)
- `CODEX_VIDEO_DESK/dashboard/server.py`·`RENDER_WORKER/worker.py`·큐·패널 bats. server.py를 **import/수정 ❌**.

## 3. 인터페이스 계약 (R → P)
- 패널이 호출할 수 있게 **`run_<track>.bat <인자>` 비대화식**(프롬프트·pause 없이) 유지 + 결과를 **`CODEX_VIDEO_DESK/RESULTS/<slug 포함>_<track>/*.mp4`** 로 떨굼(worker 탐지 규칙).
- bat 인자/슬러그 규칙 바꾸면 패널 task에 통보(계약 깨짐). 예: promo 슬러그 `{NN}_{label}_{preset}`, label `_` 금지 = `shorts/promo/PANEL_INTEGRATION_HANDOFF.md`.
- 스타일 요청 큐(`_state/style_requests.jsonl`)의 pending = 이 task(또는 주제 task)가 읽어 작성·렌더.

## 4. 트랙별 정본 (작업 유형 따라 Read)
- 카드뉴스 빌드: `_docs/CARDNEWS_BUILD.md`·`INSTRUCTIONS_CARDNEWS.md`.
- 카드뉴스영상(casual/newsroom): `_docs/INSTRUCTIONS_SHORTS.md`.
- 타이포(promo): `shorts/promo/README.md`(+ `GUIDE_BEST_TYPO_AD.md`·`STYLE_CATALOG.md`). 주제→MD = `TOPIC_TO_PROMO.md`(주제 task 정본 참조).
- 실사AI: `shorts/promo_ai/README.md`·`WORKFLOW.md`·`MEME_TO_VIRAL.md`.

## 5. 함정 / 규칙
- `.bat/.ps1` = CRLF + 한글 BOM, 중복 금지(I·STEP7). TSX 샌드박스 렌더 불가 → 렌더PC 검증.
- casual/newsroom 엔진 무수정 원칙(트랙 추가는 비파괴).

## 6. 시작 명령
`shorts/RENDER_TASK.md 읽고 shorts/·cardnews/ 콘텐츠·렌더만. 패널 server.py 안 건드림.`
