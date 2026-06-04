# README_FOR_AI

> AI(Claude / Codex / 기타)가 이 프로젝트에서 **가장 먼저 읽어야 하는 파일**.
> 사람이 읽어도 무방하지만 1차 독자는 AI.

---

## 이 폴더가 무엇인가

폰스팟 카드뉴스 → 쇼츠 영상 자동화 프로젝트. 카드뉴스 단계에서 생성된 `articles/<slug>.json` / `images/<slug>/*.png` / `output/<slug>/captions.md`를 입력으로 받아 60초 이내 세로형(1080×1920) 쇼츠 영상(.mp4)을 만든다.

**Claude 기본 빌드**와 **Codex 실험 빌드**가 한 폴더 안에 공존한다. 둘은 동일 입력을 공유하되, 빌드 산출물 경로·일부 컴포넌트는 분리되어 있다.

---

## 절대 룰 (모든 AI가 따를 것)

### 1. 전체 폴더를 재귀 탐색하지 말 것

이 프로젝트는 `node_modules/`, `out/`, `public/audio/`, `public/assets/` 등 대용량/바이너리 폴더를 포함한다. 무차별 재귀 탐색은:

- 컨텍스트(토큰) 폭증
- 무관 파일 노출 → 잘못된 추론
- 응답 속도 저하

를 일으킨다. **반드시 아래 "읽을 파일 순서"를 지킨다**.

### 2. 읽을 파일 순서 (★ 항상 이대로)

1. `harness/README_FOR_AI.md` ← 지금 이 파일
2. `harness/ACTIVE_TASK.md` ← 현재 작업 컨텍스트
3. `harness/PIPELINE_SUMMARY.md` ← 전체 흐름·핵심 파일 목록
4. **필요한 경우에만** `harness/CAPTION_RULES.md`
5. **필요한 경우에만** `harness/VISUAL_RULES.md`
6. **필요한 경우에만** `harness/QUALITY_RULES.md`
7. 그 후 **필요한 소스만** `src/` 또는 `scripts/`에서 **직접 지정**해서 확인 (재귀 탐색 ❌)

### 3. 절대 우선 탐색하지 말 것 (블랙리스트)

다음은 작업 지시가 명확히 없으면 **읽지도 말고 스캔하지도 말 것**:

- `node_modules/`
- `out/`
- `out_codex/`
- `hyperframes_codex/`
- `public/audio/`
- `public/assets/1.png` ~ `public/assets/5.png`
- `*.mp4`
- `*.mp3`
- `*.codexbak_*`
- `*.codexfixbak_*`

추가 제외 룰은 `harness/IGNORE_RULES.md` 참조.

---

## Claude vs Codex 트랙 구분

### Claude 기본 빌드
- 실행 파일:
  - `run_B_casual.bat` — 단일 캐주얼 쇼츠 빌드
  - `run_B_batch.bat` — 여러 슬러그 일괄 빌드
- 출력 경로:
  - `out/` — 렌더링된 mp4
  - `upload/` — SNS 업로드 패키지 (mp4 + 캡션 md)

### Codex 실험 빌드
- 실행 파일:
  - `run_codex_casual.bat` — Codex 버전 캐주얼 빌드
  - `run_codex_hyperframes.bat` — Codex HyperFrames 비교 빌드
- 출력 경로:
  - `out_codex/` — Codex 빌드 mp4
  - `upload_codex/` — Codex 빌드 업로드 패키지
- 백업 파일:
  - `*.codexbak_*`, `*.codexfixbak_*` (Codex가 자체 수정 전 보존)

### 어느 트랙으로 작업하나
`harness/ACTIVE_TASK.md`의 `current_track` 필드 확인. 없으면 Claude 기본(`casual`)을 가정.

---

## 신규 작업 시작 시 체크리스트

- [ ] `harness/ACTIVE_TASK.md` 업데이트 (current_slug, current_track, status)
- [ ] 카드뉴스가 먼저 빌드되어 있는지 확인 (`articles/<slug>.json`, `images/<slug>/*.png`, `output/<slug>/captions.md` 존재)
- [ ] 필요한 룰 문서만 읽기 (CAPTION/VISUAL/QUALITY)
- [ ] 작업 후 `harness/REPORTS/last_build.md` 또는 `last_review.md` 갱신

---

## 빠른 사용 (사람용)

| 시나리오 | 명령 |
|---|---|
| 캐주얼 영상 1건 | `run_B_casual.bat` |
| 여러 건 일괄 | `run_B_batch.bat` |
| Codex 비교 빌드 | `run_codex_casual.bat` |
| TypeScript 검사 | `node_modules\.bin\tsc.cmd --noEmit` |
| 품질 검사 | `py scripts\verify_video_quality.py <mp4>` |

상세는 `harness/COMMANDS.md` 참조.

---

## Codex-only layer

- Location: `codex/`
- Claude default work: ignore `codex/` unless the user explicitly asks.
- Codex work: after the shared harness files, read `codex/README_FOR_CODEX.md` and `codex/CODEX_MEMORY.md`.
- Codex outputs must stay in `out_codex/` and `../upload_codex/`.