# PhoneSpot 업데이트 정리 (2026-06)

이번 작업에서 구현·수정한 내용 전체 기록. 세부는 같은 폴더의
`IMAGE_CONTENT_MATCH_AND_IMPORT_REVIEW_GUIDE.md`(이미지 검수/중복/그림내용 매칭) 참고.

핵심 원칙: 모든 신규 기능은 **graceful 폴백**(모델/조건 없으면 기존 동작) + **검증된 것만 기본 활성**.
실제 렌더/CLIP 품질은 개발 샌드박스에서 못 돌리므로 **PC에서 확인 필요**.

---

## 1. 이미지 내용(CLIP) 매칭 + import 검수 (영상)

- 다운로드한 GPT 그림을 **파일명이 아니라 그림 내용**으로 요청에 자동 배정 제안 → 패널 검수창에서
  썸네일·신뢰도·중복경고 확인 후 확정 → 라이브러리에 정확한 이름으로 복사.
- 렌더 매칭도 그림 내용 기준이라, 이름이 틀려도 내용으로 재사용.
- 모델: `jinaai/jina-clip-v1`(이미지·텍스트 같은 768공간, 다국어).
- 신규: `shorts/scripts/codex_image_embed.py`, `codex_import_propose.py`.
- 수정: `codex_import_downloads.py`(확정매핑 소비), `codex_semantic_visual_match.py`(그림내용 보조매칭).
- 패널 버튼 **"2. 이미지 가져오기 + 렌더"** → 제안→검수→확정.

## 2. 중복 건너뛰기

- 새 그림이 기존 라이브러리 그림과 거의 같으면(`DEDUP_SKIP`=0.95) 검수창에서 기본 "사용 안 함"으로
  잡고 "기존 X 자동 재사용" 안내. 0.90~0.95는 "중복 가능" 경고만.

## 3. 카드뉴스 이미지 자동 배정 (신규, 버튼 3-2)

- 카드뉴스는 슬라이드 순서대로 1.png~N.png. 다운로드 그림을 **슬라이드 설명(prompt.md) ↔ 그림 내용**
  으로 매칭해 N.png 로 자동 배정 제안 → 검수창 확인 → `cardnews/images/<slug>/` 에 복사.
- 렌더 큐 안 씀(확정=복사까지). 그 뒤 "4. 카드뉴스 생성".
- 신규: `shorts/scripts/cardnews_import_propose.py`(엔진은 codex_image_embed 재사용).
- 카드뉴스 이미지는 1회용이라 라이브러리 재사용/중복제거는 적용 안 됨(편의 기능).

## 4. JSON 손상 복구 + 재발 방지 (중요 버그)

- 증상: `LATEST_PROMPT.json` 끝에 NUL 4275바이트 → propose/import/렌더/패널이 전부 파싱에서 죽어
  버튼2 무반응. 원인: 원본 `cardnews/output/<slug>/codex_illustration_requests.json` 이 깨졌고
  `codex_refresh_workbench.py` 가 그대로 복사(copy2)해 전파.
- 유력한 근본 원인: **Google Drive 동기화**(RESULTS 폴더에 `.tmp.drivedownload/.driveupload` 발견).
  드라이브 부분 동기화가 파일을 반쪽(NUL)으로 만들 수 있음.
- 수정:
  - `codex_refresh_workbench.py`: 그대로 복사 → **관대 파싱 후 원자적(os.replace) 재작성**.
    원본이 깨져도 LATEST_PROMPT.json 은 항상 유효.
  - `codex_import_propose.py` / `codex_import_downloads.py` / `server.py(prompt_payload)`:
    NUL/꼬리 쓰레기를 만나도 첫 JSON 객체를 복원하는 **관대 로더**.
- 권고: 능동 작업 폴더는 드라이브 스트리밍 밖에 두거나 "오프라인 사용 가능"으로.

## 5. 렌더 "헛 재시작"(worker lease expired) 수정

- 증상: Step 5(Remotion) 가 90초 넘게 조용하면 job 리스가 만료돼 살아있는 워커의 렌더가 재시작.
- 원인: job 리스가 "로그 출력 시"에만 갱신됐음.
- 수정: `/api/worker/check`(워커가 5초마다 보내는 핑)가 **job 리스를 갱신**하도록.

## 6. 렌더 속도

- **#1 동시성**: `--concurrency=2` 하드코딩 → 환경변수 `PHONESPOT_RENDER_CONCURRENCY`(기본 `50%`).
  최적값은 `npx remotion benchmark`로 측정.
- **#3 번들 재사용**: 신규 `shorts/scripts/render_remotion_fast.mjs` — 번들을 1회만 만들고
  `src/`+`public/` 가 안 바뀌면 재사용(렌더마다 번들링 제거). 실패 시 bat 이 기존 CLI 로 자동 폴백.
- **#2 이중 인코딩 완화**: raw 를 싸게(crf=23, x264 veryfast). 최종 화질은 Step 6 가 게이트.
- **Step 6 인코딩 가속**: `finalize_sns_video.py` 프리셋 medium → **veryfast**(비트레이트 고정이라
  화질 차이 미미, 인코딩 2~3배↑). 되돌리려면 `PHONESPOT_FINAL_PRESET=faster/medium`.
- **GPU(옵트인)**: blur/box-shadow/gradient 가 많은 컴포지션은 CPU(swiftshader) 렌더가 느림.
  `setx PHONESPOT_GL angle` 로 테스트(노드 경로는 chrome-for-testing 자동). 기본 꺼짐=기존 동작.
  GPU 출력은 드라이버에 따라 다를 수 있어 결과 확인 필수.
- 측정: 렌더 후 `RESULTS\<키>\remotion_raw_render.log` 끝 `[render] done in Xs` = 순수 Step 5 시간.

## 7. 기타 편의/안정화

- **임베딩 캐시 워밍(5-1)**: 패널 시작 시 `codex_warm_embeddings.py` 를 백그라운드 실행 →
  첫 버튼2/렌더가 라이브러리 전체를 임베딩하느라 기다리지 않음.
- **워커 폴링 3초 → 1초**: 배정대기 체감 단축(`RENDER_WORKER/worker.py`). 워커 재시작 필요.
- **결과 폴더에 스크립트 보장 저장**: 렌더 후 `shorts_script.json`+`captions.md` 를 결과 폴더에
  항상 복사(Step 7 실패/드라이브 지연과 무관). `run_codex_casual.bat`.
- **실행 로그 [로그 복사] 버튼**: 드래그 없이 전체 복사.
- **헤더에 패널 버전 배지**: 현재 실행 버전 표시(재시작 반영 확인용).
- **작업표시줄 고정**: `작업표시줄에_패널_고정.bat` 더블클릭(바탕화면+시작메뉴 바로가기 생성, 고정 시도).

---

## 환경변수 노브

| 변수 | 기본 | 용도 |
|---|---|---|
| `PHONESPOT_RENDER_CONCURRENCY` | `50%` | Remotion 프레임 동시 렌더 수(숫자/`50%`/`auto`) |
| `PHONESPOT_RAW_CRF` | `23` | 중간(raw) 인코딩 품질(높을수록 빠름/작음) |
| `PHONESPOT_RAW_PRESET` | `veryfast` | 중간 raw x264 프리셋 |
| `PHONESPOT_FINAL_PRESET` | `veryfast` | 최종(Step6) x264 프리셋. 아티팩트 시 `faster`/`medium` |
| `PHONESPOT_GL` | (없음) | GPU 백엔드. `angle` 로 테스트. 없으면 CPU |
| `PHONESPOT_CHROME_MODE` | `chrome-for-testing`(GL시) | 헤드리스 GPU 디스플레이 모드 |
| `PHONESPOT_IMG_MATCH_MIN` | `0.28` | 렌더 그림내용 매칭 임계(교차모달 코사인) |
| `PHONESPOT_CARD_IMPORT_HOURS` | `12` | 카드 자동배정 후보로 볼 다운로드 최근 시간 |
| `PHONESPOT_EMBED_MODEL` | 다국어 MiniLM | 텍스트 임베딩 모델 |
| `PHONESPOT_CLIP_MODEL` | `jinaai/jina-clip-v1` | 이미지/텍스트 공용 CLIP |

설치(각 PC 1회): `shorts\SETUP_EMBED.bat` (fastembed/numpy/pillow + 텍스트·이미지 모델 다운로드).

---

## 적용/재시작 규칙

- **패널 코드(server.py)** 변경 → 핫리로드 불가. `PANEL_VERSION` 과 `start_hidden.ps1` 의
  `$expectedVersion` 을 **같이 한 칸 올린 뒤** `00_PHONE_SPOT_PANEL.bat` 더블클릭 → 버전 불일치로
  자동 재시작 → 브라우저 Ctrl+Shift+R. 헤더 배지로 반영 확인. 현재: `phonespot-web-v12`.
- **스크립트/배치(codex_*.py, run_codex_casual.bat, render_remotion_fast.mjs)** 변경 → 재시작 불필요,
  다음 실행부터 적용. 단 워커 환경변수(GPU 등)는 워커 재시작해야 상속.

---

## 정직한 한계 (PC에서 확인 필요)

- CLIP 한국어/슬라이드 ↔ 그림 실제 매칭 정확도, 임계값은 추정값 — 렌더/검수 결과로 조정.
- 렌더 속도 변경은 샌드박스에서 실측 불가 — 테스트 렌더로 화질/규격/속도 확인. GPU는 PC GPU 의존.
- 제자리 수정한 일부 .py 는 샌드박스 마운트 캐시 문제로 py_compile 직접 확인을 못 함(호스트 구조·로직은
  단위테스트로 검증). 의심되면 PC에서 `python -m py_compile <file>` 로 점검.

---

## 정리(cleanup) 내역 2026-06-06

- 삭제: 깨진 원본 백업 `*.corrupt_*` 2개, 소비 마커 `IMPORT_CONFIRMED.used.json`,
  임시 제안 `IMPORT_PROPOSAL.json`(재생성됨), `__pycache__` 2개.
- 보존(불확실): `*.bak_*` 약 189개(집 규칙 백업/복원점), `src` 의 `*.tsxbak*`,
  멀티PC 구글시트 관련 미적용 파일. GitHub 이력이 있으니 필요시 .bak 일괄 정리 가능.
