# 타이포(promo) 패널 통합 — 인수인계 (2026-06-24)

> 작성: 카드뉴스/영상 패널 task. 수신: **promo 트랙 원래 task**(정본 = `shorts/promo/README.md`).
> 한 줄 요약: **패널 "타이포 탭" UI·연결은 패널 task가 소유. promo 콘텐츠·스타일·렌더 품질은 promo task가 소유.**
> 이 문서는 둘 사이 **계약(인터페이스)** 과 패널 task가 promo 도메인에서 건드린 것만 기록. promo 내부 워크플로는 README.md가 정본.

---

## 1. 분담 (누가 무엇을 갖는가)

| 영역 | 소유 | 비고 |
|---|---|---|
| 패널 "타이포 탭" UI(목록 select·프리셋 select·렌더 버튼·로그) | **패널 task** | `server.py` INDEX_HTML `#trackTypo` + JS `promoLoad/promoRender` |
| 패널 액션 `promo_list`·`promo_render` | **패널 task** | `server.py` |
| worker 액션 `promo_render` | **패널 task** | `worker.py commands_for` |
| `run_promo.bat` **인자(비대화식) 모드 + RESULTS 복사 shim** | **패널 task가 추가**(아래 §3) | 대화식 본체는 promo task 소유 — shim만 패널 책임 |
| promo 스크립트(`promo/*.json`)·MD 편집(`promo/review/*.md`)·스타일 23·프리셋 4·SFX·음악·학습루프·렌더 품질·신규 토픽 | **promo task** | 패널은 일절 안 건드림 |

원칙: **패널은 "기존 스크립트를 골라서 렌더"만 호출.** 콘텐츠가 어떻게 보이고 들리는지는 전부 promo task.

---

## 2. 패널 ↔ promo 계약 (★ 이게 깨지면 패널 렌더가 깨짐)

흐름: 타이포 탭 → `promo_list`로 목록 → 사용자 선택 → `promo_render` → 큐 → worker → `run_promo.bat <num> <preset>`.

**계약 A — 목록 (`promo_list`)**
- `server.py promo_list`(라인 1900)가 `python scripts/promo_list.py`(cwd=shorts) 실행 후 한 줄씩 정규식 파싱:
  `^\s*(\d{3})\s+(\S+)\s+(.+?)\s+\[(\w+)\]\s*$` → `{nn, label, title, preset}`.
- **promo task가 지켜야 할 것:** `promo_list.py` 출력 포맷 `NNN  label   한글제목   [preset]` 유지. 포맷 바꾸면 패널 목록이 빈다.

**계약 B — 렌더 (`promo_render` → worker → bat)**
- 패널이 보내는 payload: `{action:"promo_render", nn, label, preset}`.
- `server.py promo_render`(라인 1914)가 **슬러그 인코딩**: `slug = "{NN}_{label}_{preset}"` (예 `001_jeongchalje_showcase`)로 큐 등록.
- `worker.py`(라인 207)가 **디코딩**: `parts=slug.split("_"); num=str(int(parts[0])); preset=parts[-1]` → `run_promo.bat <num> <preset>`.
- 결과 탐지: worker `result_after`는 `RESULTS/<폴더명에 slug 포함>/*.mp4`를 찾음. 그래서 bat이 `RESULTS/{NN}_{label}_{preset}_promo/`로 복사(아래 §3).
- **promo task가 지켜야 할 것:**
  1. `promo_get.py <n>`에서 **번호 = int(NNN)** 매핑 유지(현행 그대로).
  2. label(slug)에 **언더스코어(`_`) 넣지 말 것.** 디코딩이 `parts[0]=NN, parts[-1]=preset`만 가정. label에 `_`가 들어가면 preset 파싱이 깨짐. (현행 label은 전부 `_` 없음.)
  3. `run_promo.bat`이 `<num> <preset>` 2-인자 비대화식 호출을 계속 받아야 함(§3).

---

## 3. 패널 task가 promo 도메인에서 건드린 것 = `run_promo.bat` (비파괴 shim)

대화식 본체는 그대로 두고, **인자가 있으면 비대화식**으로만 분기. 변경 라인(현행):
- L17 `if not "%~1"=="" ( set "NUM=%~1" & set "NONINT=1" )` — 1번 인자=번호면 NONINT 모드.
- L18 `if "%NUM%"=="" set /p NUM=...` — 인자 없을 때만 번호 프롬프트(기존 동작).
- L23 `if not "%~2"=="" set "PRESET=%~2"` — 2번 인자로 프리셋 오버라이드(promo_get 기본값 위에).
- L46-49 `if defined NONINT (...)` — 렌더 성공 후 `RESULTS/%NN%_%SLUG%_%PRESET%_promo/`로 복사(worker 탐지용).
- L54 `if not defined NONINT pause` — 비대화식이면 끝에 멈추지 않음(worker 행 방지).

**promo task 주의:** `run_promo.bat`을 리팩터/재생성할 때 위 5개 분기를 보존하거나, 보존 불가하면 패널 task에 알릴 것. (STEP 7 리포위생: byte-동일 사본 만들지 말고 이 파일 단일 유지.)

---

## 4. promo task가 이어받는 "기능" (패널은 호출만, 내용은 너희가)

지금 패널은 **기존 17개 스크립트 + 프리셋 4종**만 노출. 다음은 전부 promo task 영역:
- 스크립트 신규/수정(`promo/review/*.md` → JSON), 한글 제목·후킹·비트 구성.
- 스타일 23종 품질, 새 스타일 추가(파일 추가 시 자동 등록).
- SFX/음악 매칭, 무드풀, 학습 루프(`_LEARN.md`, `promo_score.py`).
- 렌더 품질 파라미터(crf/preset/concurrency 등은 `run_promo.bat` 본체).

패널 쪽 확장이 필요하면(요청만, 구현은 패널 task):
- 스타일(23종) 개별 선택 노출 — 현재는 프리셋 4종만. 필요하면 `promo_list`에 styles 배열 추가 + UI select 확장.
- 스크립트별 썸네일/프리뷰, 배치 렌더, 결과 미리보기.
- 패널에서 MD 편집 — **현재 의도적으로 제외**(편집은 promo 워크플로 유지).

---

## 5. 빠른 검증 (promo task가 계약 확인용)

```
# 목록 포맷 확인 (계약 A)
cd shorts && python scripts/promo_list.py        # NNN  label  제목  [preset] 유지되는지

# 비대화식 렌더 (계약 B) — 번호 1, 프리셋 showcase
shorts\run_promo.bat 1 showcase
#  -> promo/out/001_jeongchalje_showcase.mp4
#  -> CODEX_VIDEO_DESK/RESULTS/001_jeongchalje_showcase_promo/...mp4  (worker가 이걸 잡음)

# 대화식(기존)도 그대로 동작하는지
shorts\run_promo.bat                              # 번호 프롬프트 + 끝에 pause
```

관련 파일: `server.py`(v38, promo_list L1900 / promo_render L1914) · `worker.py`(L207) · `run_promo.bat`(L17·18·23·46·54).
