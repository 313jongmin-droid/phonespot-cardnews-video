# 폰스팟 제작 시스템 웹 허브 전환 기획서 (사내 인원 기준)

> 작성 2026-10-08 · 소유 = 패널 엔진 task (`CODEX_VIDEO_DESK/PANEL_TASK.md`) · 상위 = `_docs/SYSTEM_MAP.md` A단원
> 상태: **기획(미구현)**. 사장님 검토 → §8 결정사항 확정 → §5 단계 순서로 구현.
> 표기: [사실] = 코드/공식문서로 확인 · [미확인] = 확인 못 함 · [가정] = 기획 전제(결정 시 바뀜)

---

## 0. 한 장 요약

- **목표**: 관리(접수·현황·기록·결과·자산)는 **웹 허브 1곳**에 통합하고, 렌더는 **각 제작자 PC의 에이전트**가 한다. 제작자는 웹에서 설치 링크로 에이전트를 1회 설치.
- **핵심 원칙**: 렌더 코드(`shorts/`·`cardnews/` 스크립트·`run_*.bat`)는 **수정하지 않고 호출만**(Windows 그대로). 바뀌는 건 패널 task 영역(`server.py`·`remote_queue.py`·`worker.py`·설치기).
- **이미 있는 기반 [사실]**: 워커 pull 프로토콜(register/claim/log/check/complete/result), 잡별 패키지 zip 다운로드(`package_bytes`), 결과 업로드, 원클릭 셋업, 버전 보고.
- **막는 것 [사실]**: 패널 PC에서 직접 실행하는 액션 14개(아래 §2.2 B1), 전역 "현재 슬러그" 상태(B2), 다운로드 폴더 직접 접근(B3), Drive 허브 의존(B4), 인터넷용 인증 부재(B5).
- **단계**: P1 에이전트화(로컬에서 검증) → P2 자산·결과 허브화(로컬에서 검증) → P3 클라우드 이전+로그인 → P4 설치 배포·버전 강제·배정. **클라우드 이전은 마지막** — 앞 단계는 지금 패널에서 그대로 검증 가능, 운영 중단 없음.
- **비용 하한(예시)**: 서버 Lightsail 서울 Linux 2GB **$12/월** + 저장소 Cloudflare R2 **10GB까지 무료** + 로그인 Cloudflare Access(무료 플랜 50명, [미확인] 아래 §4.1). 렌더 비용 0(제작자 PC).

---

## 1. 범위·전제

| 항목 | 내용 |
|---|---|
| 사용자 | **사내 인원만** [가정: 인원 N명, §8 D7]. 외부 공유 없음 |
| 역할 | 관리자(사장님) / 제작자. 제작자 = 웹 로그인 + 자기 PC에 에이전트 |
| 유지 | 3-task 분할(CLAUDE.md STEP 0-6), 기사 작성 = Claude(로컬 PC) → git push, 광고운영(Apps Script)·텔레그램 listener(`automation/`)는 범위 밖 |
| 비범위 | 렌더 엔진 Linux 이식, 서버리스 렌더, 외부 사용자, 결제 |
| 성공 기준 | ① 사무실 밖(폰 LTE)에서 로그인 → 작업 접수·진행·결과 확인 ② 로컬 PC 꺼져도 허브는 응답, 제작자 PC가 켜지면 잡 처리 ③ 새 PC = 설치 링크 1개 + 로그인으로 렌더 참여 ④ 기존 산출물과 동일 결과(같은 slug → 같은 mp4 구성) |

---

## 2. 현행 구조 (사실)

### 2.1 구성
| 요소 | 위치 | 사실 |
|---|---|---|
| 패널 서버 | `dashboard/server.py` (110KB) | `ThreadingHTTPServer`, 기본 바인드 `0.0.0.0` (`server.py:2376`). 액션 블록 34개(L1900~2349, 이름 35개 — `card_to_video`는 `video_prepare` L1982 별칭) |
| 화면 | `dashboard/static/index.html` (92KB) | 요청마다 디스크에서 로드 |
| 렌더 큐 | `dashboard/remote_queue.py` | JSON 파일 + 잡 로그 파일(`TEMP/remote_logs`). 잡 필드: id·action·slug·status·worker_id·target_worker·retry_count·lease_epoch 등 (`enqueue` L211) |
| 잡 패키지 | `remote_queue.py:386 package_bytes` | 기사 JSON + `cardnews/images/<slug>` + `cardnews/output/<slug>` + ILLUSTRATION_DROP 요청분 + CHUNK_OVERRIDES + **전역 `LATEST_SLUG.txt`/`LATEST_PROMPT.json/md`** 를 zip |
| 워커 | `RENDER_WORKER/worker.py` (v7) | 서버 주소 = env `PHONESPOT_PANEL_URL` 또는 `RENDER_WORKER/panel_url.txt` (L27~29). 패키지 받아 리포 루트에 풀고(`safe_extract` L143) `commands_for`(L269) 실행 → 결과 업로드 |
| 워커 실행 명령 | `commands_for` | `video_import_render`(=`codex_import_downloads.py`+`run_codex_casual.bat`), `video_render_selected`, `promo_render`(`run_promo.bat`), `cover_render`(`run_cover.bat`) — **Windows `cmd /c`** |
| 렌더 본체 | `shorts/run_codex_casual.bat` 223줄 | Python·mjs 스크립트 25종 순차 호출. `shorts/scripts/*.py` 11,373줄, 11개 파일에 Windows 의존 참조 |
| 셋업 | `CODEX_VIDEO_DESK/부사수PC_원클릭_셋업.bat` (103줄) | winget(Git/Node/Python) → `git clone` → `SETUP_FULL_PRODUCER.bat`(npm install, pip: edge-tts·playwright·fastembed·faster-whisper 등, playwright chromium, 임베딩 ~1GB) → Google Drive 설치(선택) |
| 공용 일러스트 | Drive `PhoneSpot_Library` + `shorts/config/library_share_path.txt` | `codex_library_sync.py` 양방향 병합 |
| 자산 크기(로컬 PC 실측) | — | 일러스트 198MB, 카드 이미지 297MB, 카드 output 43MB, RESULTS 64MB(mp4 5개, 평균 12.6MB·최대 13.2MB) |
| 코드 원격 | GitHub `313jongmin-droid/phonespot-cardnews-video` | 셋업이 clone하므로 각 PC에 저장소 읽기 권한 필요 |

### 2.2 웹 전환 걸림돌 (B1~B7)
- **B1. 패널 PC 직접 실행 액션 14개** [사실]: `run_job` 10곳(sync_cardnews L1905·library_sync·library_dedup·library_backup·producer_check·video_prepare L1988·card_render L2250·work_queue_refresh·system_upload·system_update L2300) + 직접 `subprocess` 4곳(video_import_propose L1998·card_import_propose L2073·promo_list L2161·promo_generate L2198). 별도로 panel_update_restart(L2280)는 서버 자기 재시작. 그리고 `run_job`은 전역 단일 슬롯(`server.py:322~326`, 실행 중이면 "busy") → 다인원 동시 사용 불가.
- **B2. 전역 "현재 슬러그" 상태** [사실]: `LATEST_SLUG.txt`·`LATEST_PROMPT.json/md`(DESK 루트)가 패키지에 그대로 들어감. 청크 편집은 `cardnews/output/<slug>/shorts_script.json`이 없으면 전역 `shorts/public/shorts_script.json`에 씀(`script_path_for_slug` L730). → 두 사람이 다른 slug를 동시에 다루면 섞임.
- **B3. 다운로드 폴더 직접 접근** [사실]: `video_import_confirm`·`card_import_confirm`·가져오기 제안·`/api/illust-thumb`이 `Path.home()/Downloads`(L39)를 읽음 = 서버가 깔린 PC의 다운로드 폴더.
- **B4. Drive 허브·메인 PC LAN sync 의존** [사실]: 일러스트(Drive), 카드 이미지(`SYNC_CARDNEWS_WORKSPACE_FROM_MAIN_PC.ps1`, 메인 PC 192.168.0.7).
- **B5. 인터넷용 인증 없음** [사실]: v60 접근제어는 LAN 전제(Host 검증 + 토큰 1개 공용). `/api/worker/*`는 Host만 확인.
- **B6. 폴더 열기 액션** [사실]: `open_*` 4개가 `os.startfile` = 서버 PC 탐색기. 웹에선 의미 없음.
- **B7. 서버 자체의 Windows 의존** [사실]: `pythonw`/`CREATE_NO_WINDOW`/`powershell`/`os.startfile`. 단, **v60 격리 검증에서 server.py는 Linux에서 기동·API 동작 확인됨** → 위 의존은 B1·B6 액션에 몰려 있음.

---

## 3. 목표 구조

```
[제작자 브라우저] ──HTTPS(로그인)──▶ [웹 허브]  ◀──HTTPS(워커 토큰, 바깥으로만 연결)── [제작자 PC 에이전트 ×N]
                                     │ server.py(Linux)                                │ worker.py v8 + 기존 렌더 코드(Windows)
                                     │ DB(잡·워커·사용자·자산목록)                       │ 로컬 자산 캐시(해시로 동기화)
                                     │ 저장소(결과 mp4·카드이미지·일러스트·로그)          │ 다운로드 폴더 스캔(자기 PC)
                                     └ git pull ◀── GitHub ◀── 로컬 PC(Claude 기사 작성·코드 push)
```

- **웹 허브(관리층)**: 화면, 잡 접수·배정·취소·재시도, 진행 로그, 결과 보관/미리보기/다운로드, 자산 목록(무엇이 어디 있나), 사용자·워커 관리, 설치 링크 발급, 버전 정책. **렌더·임베딩은 안 함**(작은 서버로 충분).
- **에이전트(만드는층)**: 지금 `worker.py`의 확장. 잡을 가져와 **필요 자산만 해시로 받아** 기존 bat/스크립트 실행 → 결과·로그·새로 생긴 자산을 허브로 업로드. 자기 PC 다운로드 폴더 스캔(가져오기 제안)도 에이전트 잡.
- **데이터 흐름(영상 1편)**: 기사(git) → 허브 → [잡: 이미지 프롬프트 준비@에이전트] → 제작자가 이미지 생성(수동) → [잡: 가져오기 제안@그 제작자 PC] → 웹에서 확정 → 이미지가 허브 저장소로 업로드 → [잡: 렌더@아무 에이전트] → 결과 mp4 허브 보관.

---

## 4. 설계 상세

### 4.1 인프라 선택지 (D1·D2·D3)
| 안 | 구성 | 비용 [출처] | 장점 | 한계 |
|---|---|---|---|---|
| **A** | AWS Lightsail 서울 Linux 2GB(2vCPU·60GB·3TB 전송) + Cloudflare Tunnel + Cloudflare Access + R2 | 서버 **$12/월**(1GB는 $7) [Lightsail 공식, 페이지 갱신 2026-09-25] · R2 무료 10GB/월, 초과 $0.015/GB·월, 송신 무료 [R2 공식] · Access 무료 플랜 50명 [미확인: 공식 페이지에서 수치 확인 실패, Cloudflare 2020 블로그·제3자 다수가 50명 보고] | 서버 포트 개방 0(Tunnel), 로그인 코드 직접 안 짬(Access가 구글 로그인 처리), 서울 지연 낮음 | Cloudflare에 도메인(DNS) 필요 [D2], 클라우드 2곳 계정 |
| B | 사무실 상시 PC + Tunnel + Access | 서버 $0 | 가장 쌈 | 그 PC가 꺼지면 허브 정지 → 성공기준 ② 불충족 |
| C | GCP e2-micro Always Free(1GB) | $0 | 무료 | **미국 3개 리전만 무료**(서울 생성 시 과금) [제3자 다수, 공식 미확인], 1GB 메모리 |
| D | A와 같되 로그인을 앱이 직접(구글 OAuth) | 서버 $12/월 | Cloudflare 의존 축소 | 인증 코드·세션·보안 직접 구현(작업량↑) |

- 서버 사양 근거: 허브는 렌더를 안 하므로 CPU 부담 작음. 단 `package_bytes`가 zip을 **메모리(BytesIO)** 에 만듦 → 2GB 권장(P2에서 저장소 직행 다운로드로 바꾸면 1GB도 가능 [가정]).
- 백업: Lightsail 스냅샷 $0.05/GB·월 [Lightsail 공식] + DB 일일 덤프를 R2에.

### 4.2 인증·권한
- **사람**: (안 A) Cloudflare Access가 허브 앞에서 구글 로그인 + 허용 이메일 목록. 허브는 Access가 넘겨준 사용자 이메일 헤더로 사용자 식별 → 역할(관리자/제작자) 매핑.
- **에이전트**: 2중. ① Cloudflare Access **서비스 토큰**(계정당 50개 [사실: Cloudflare One account limits]) ② 허브 자체 **워커별 토큰**(설치 시 발급, 폐기 가능, DB에 해시 저장). v60의 "Host만 확인"(`/api/worker/*`)은 P3에서 토큰 필수로 변경.
- **권한 매트릭스**: 제작자 = 잡 접수·자기 다운로드 가져오기·결과 보기/받기·자기 워커 관리. 관리자 = + 사용자/워커 승인·폐기, 삭제, 버전 정책, 설정.
- **코드 실행 위험**: 허브가 에이전트에 "무엇을 실행할지"를 보낸다 → 허브 탈취 = 전 제작자 PC 위험. 대책: 에이전트는 **허브가 보낸 명령 문자열을 실행하지 않고** 로컬 화이트리스트(`commands_for`)의 액션 이름만 받는다(현재 구조 유지), 코드 업데이트는 서명/고정 출처만(§4.7).

### 4.3 데이터 모델 (SQLite로 시작 [가정], 단일 서버라 충분)
| 테이블 | 주요 필드 |
|---|---|
| users | email, role, active |
| workers | id, owner_email, name, version, token_hash, capabilities, ready, issues, last_seen |
| jobs | id, action, slug, params(JSON), requested_by, target_worker, status, worker_id, lease_epoch, retry_count, created/started/finished, exit_code, message |
| job_logs | 파일(저장소) — 현행 `TEMP/remote_logs/<id>.log` 방식 유지 |
| articles | slug, git_sha, updated_at (본문은 git 체크아웃 파일) |
| assets | sha256, kind(card_image/illustration/override/script), logical_path, size, uploaded_by, created_at |
| slug_assets | slug ↔ asset 매핑(카드 1~5.png, 청크 오버라이드, shorts_script 등) |
| results | job_id, slug, track, storage_key, size, created_at, retention_until |
| audit | who, what, when (삭제·권한 변경) |
- 현행 JSON 큐 → DB 이관 스크립트 1회(P2).

### 4.4 API 변경
- **유지(호환)**: `/api/worker/register|claim|log|check|complete|result|package`, `/api/action`, `/api/state`, `/api/jobs`, `/api/job_log`.
- **추가**: `GET /api/assets/manifest?slug=` (필요 자산 해시 목록) · `GET/PUT /api/assets/<sha256>` (저장소 직행) · `POST /api/worker/enroll` (설치 토큰 → 워커 토큰 교환) · `GET /api/install` (설치 스크립트/버전 정보) · `POST /api/imports/propose_result` (에이전트가 다운로드 폴더 후보+썸네일 업로드).
- **잡 파라미터**: 현재 잡은 `slug`만 가짐 → `params`(JSON) 추가(promo 번호·preset, cover variant, 요청자 PC 지정 등). 전역 `LATEST_*` 대신 잡 파라미터로 전달(B2 해소).

### 4.5 액션 재분류 (34개 → 허브 / 에이전트 잡 / 대체·폐기)
| 분류 | 액션 |
|---|---|
| **허브에서 처리(데이터 조작)** | style_request, style_pending, remote_job_cancel, remote_job_retry, update_visual, adjust_chunk, set_section_chunks, delete_slug(허브 데이터+결과), card_import_confirm·video_import_confirm(업로드된 후보로 확정), video_render_selected·cover_render·promo_render(큐 등록만), telegram_card_summary·telegram_test(텔레그램 키를 허브에 둘지 D8) |
| **에이전트 잡으로 전환(B1)** | video_prepare(=card_to_video), video_import_propose·card_import_propose(**요청자 본인 PC 지정**), card_render(`run_pngs.bat`), producer_check(각 PC가 결과를 허브에 보고), library_dedup, promo_generate(현재 서버에서 `promo_generate.py` 실행 후 큐 — 생성 단계를 잡으로), promo_list(스크립트가 Linux에서 도는지 P1에서 확인 [미확인]) |
| **허브 기능으로 대체** | library_sync·library_backup → 자산 허브(§4.6)·서버 백업 / sync_cardnews(메인 PC LAN sync) → 카드 이미지 허브 업로드 / open_* 4개 → 웹 미리보기·다운로드 / work_queue_refresh → 허브 DB 조회 |
| **웹에서 제거(로컬 PC 전용 유지)** | system_upload(git push = 로컬 PC 개발 기능, CLAUDE.md STEP 0), system_update·panel_update_restart → 에이전트 자동 업데이트(§4.7)·서버 배포 절차로 분리 |
- 위 분류 중 개별 스크립트의 입력·출력 경로는 **P1 착수 시 스크립트별로 확인 후 확정**(현재는 액션 단위 분류).

### 4.6 자산 동기화
- **원칙**: 모든 공유 파일은 **내용 해시(sha256)로 식별**. 에이전트는 잡 시작 전 manifest를 받아 **없는 해시만** 내려받음 → 같은 파일 재전송 0.
- 카드 이미지·청크 오버라이드·shorts_script: slug 단위 manifest.
- 일러스트 라이브러리(198MB): 허브가 정본. 에이전트가 새 일러스트를 만들면(가져오기 확정) 허브로 업로드 → 다른 PC는 다음 잡에서 받음. **Drive 허브 대체**(전환 기간엔 병행, D9).
- 임베딩 모델(~1GB)·node_modules·크롬: 설치 시 1회(현행 셋업 재사용), 허브 전송 대상 아님.
- 결과 mp4: 허브 저장소. 보관 기간 정책(D6).

### 4.7 설치·업데이트
- **설치 흐름**: 관리자가 웹에서 "PC 추가" → 1회용 설치 토큰이 박힌 설치 명령/파일 다운로드 → 실행 시 기존 `부사수PC_원클릭_셋업.bat` 경로 재사용 → 마지막에 `POST /api/worker/enroll`로 워커 토큰 수령·등록 → 웹에 그 PC 환경점검 결과(PASS/FAIL) 표시.
- **코드 배포(D4)**: (a) git 유지 — 각 PC에 저장소 **읽기 전용** 권한(배포 키/토큰) 필요, 현행 `auto_update.cmd` 그대로 / (b) 허브가 버전별 번들 배포 — PC에 GitHub 권한 불필요, 번들 빌드·서명 절차 추가.
- **버전 강제**: 허브가 `min_worker_version` 보유, 미만 워커에는 잡 미배정 + 웹에 "업데이트 필요" 표시(현재 등록 시 `version` 이미 보고 [사실]).

### 4.8 배정 정책 (D5)
- (a) 요청자 PC 우선 → 없으면 대기 / (b) 공용 풀(아무 준비된 PC) / (c) 혼합: **가져오기 제안은 요청자 PC 고정**(그 PC 다운로드 폴더가 대상이므로 필수), 렌더는 공용 풀.
- 현재 잡에 `target_worker` 필드 이미 있음 [사실] → (c)는 필드 활용으로 구현 가능.

### 4.9 Claude·기사 흐름
- 변경 없음: Claude(로컬 PC)가 `cardnews/articles/*.json` 작성 → push. 허브는 GitHub에서 주기적 `git pull`(또는 push 웹훅) → articles 테이블 갱신.
- 허브에 GitHub **읽기 전용** 배포 키 필요.

---

## 5. 단계별 로드맵 (각 단계 끝에 운영 가능 상태 유지)

| 단계 | 작업 | 변경 파일(패널 task 범위) | 완료 기준(검증) |
|---|---|---|---|
| **P0 결정** | §8 D1~D9 확정, 계정·도메인 준비 | 없음 | 결정표 채움 |
| **P1 에이전트화** (로컬 허브 그대로) | B1 14개 액션을 큐 잡으로(또는 §4.5대로 허브 기능으로) 전환(`commands_for` 확장), `run_job` 전역 슬롯 제거, 잡 `params` 추가, 전역 `LATEST_*`·전역 shorts_script 의존 제거(B2), 가져오기 제안을 "요청자 PC 지정 잡"으로(B3) | server.py, remote_queue.py, worker.py(v8), static/index.html | ① 액션 핸들러 안 `run_job`·`subprocess` 호출 0곳(grep, panel_update_restart 제외) ② 같은 slug로 기존 경로 vs 신경로 결과 동일(파일 목록·mp4 길이) ③ 두 slug 동시 진행 시 섞임 0 ④ 렌더PC 로그로 확인 |
| **P2 자산·결과 허브화** (로컬 허브 그대로) | 저장소 추상화(로컬 디스크/R2 교체 가능), 해시 manifest 동기화, 결과 허브 보관·웹 미리보기/다운로드, JSON 큐→SQLite 이관, 일러스트 허브(Drive 병행) | server.py, remote_queue.py(→DB), worker.py, 신규 storage 모듈 | ① 빈 캐시 PC가 manifest만으로 렌더 성공 ② 두 번째 잡에서 재전송 0바이트 ③ 이관 전후 잡 수·로그 일치 |
| **P3 클라우드 이전+로그인** | Linux 서버 배포, Tunnel+Access(또는 D), 워커 토큰 필수, GitHub pull, 백업 | 배포 스크립트, server.py(인증 헤더 처리) | ① 폰 LTE에서 로그인 → 접수 → 사무실 PC 렌더 → 결과 재생 ② 비로그인·무토큰 403 ③ 로컬 PC 꺼도 허브 응답 ④ 백업 복원 리허설 1회 |
| **P4 설치 배포·운영** | 설치 링크·enroll, 버전 강제, 배정 정책, 사용자/워커 관리 화면, 감사 로그 | worker 설치기, server.py, index.html | ① 새 PC: 링크 1개+로그인으로 첫 잡 성공 ② 구버전 워커 잡 미배정 ③ 워커 토큰 폐기 즉시 차단 |

- P1·P2는 **지금 로컬 패널에서 검증**하므로 클라우드 비용 0. P3부터 과금.
- 렌더 결과물 검증은 CLAUDE.md STEP 0 원칙대로 **렌더 PC 로그 기준**.

---

## 6. 비용 계산 (안 A 기준, USD)

- 고정: 서버 $12/월(2GB) 또는 $7/월(1GB) [Lightsail 공식] + 스냅샷 $0.05/GB·월 × 디스크 사용량.
- 저장소(R2): 월 비용 = max(0, 저장량GB − 10) × $0.015. 송신 무료 [R2 공식].
  - 초기 자산 ≈ 0.54GB(일러스트 0.198 + 카드 이미지 0.297 + output 0.043).
  - 결과: mp4 평균 12.6MB 실측 → 월 V편이면 +0.0126·V GB/월. V=100 → +1.26GB/월 → **무료 10GB 소진까지 ≈ (10−0.54)/1.26 ≈ 7.5개월**, 이후 GB당 $0.015/월(예: 20GB = $0.15/월).
  - 보관 기간(D6)을 두면 상한 고정.
- 로그인: Access 무료 플랜 범위면 $0, 초과 시 사용자당 과금 [제3자 보고 $7/사용자·월, 미확인].
- 도메인: 기존 도메인을 Cloudflare DNS로 쓸 수 있으면 추가 0 [D2].
- **렌더 컴퓨팅: $0** (제작자 PC).

---

## 7. 리스크·한계

| 리스크 | 영향 | 대응 |
|---|---|---|
| PC별 환경 편차 | 설치 실패·렌더 실패 | 환경점검 결과를 허브에 상시 표시, 준비 안 된 PC엔 잡 미배정(현 readiness 로직 확장) |
| 허브 탈취 | 전 PC 위험 | 액션 이름 화이트리스트만 전달, 워커 토큰 개별 폐기, 코드 배포 출처 고정 |
| 클라우드 운영 부담 | 장애·백업 책임 발생 | 단일 서버+일일 백업+복원 리허설(P3 완료기준) |
| edge-tts | 비공식 엔드포인트 | **에이전트(제작자 PC)에서 실행**하므로 현행과 동일 — 허브 이전과 무관 |
| Remotion 라이선스 | 회사 인원이 기준 초과 시 회사 라이선스 필요 | 웹 전환과 무관하게 **현재도 해당**. 라이선스 원문(GitHub `LICENSE.md`)은 "직원 3명 이하 영리조직 무료" 취지 [검색 인용, 원문 직접 열람 실패 → D7에서 확인] |
| 전환 중 이중 운영 | 혼선 | P1·P2는 기존 패널 안에서 진행, P3 전환일 1회 컷오버 |
| 일러스트 Drive→허브 | 두 정본 공존 기간 충돌 | 전환 기간 단방향(허브 정본) 결정 D9 |

---

## 8. 결정 필요 사항 (사장님)

| # | 질문 | 선택지 |
|---|---|---|
| D1 | 허브 서버 | A Lightsail 서울 2GB / A' 1GB / B 사무실 상시 PC / C GCP 무료(미국) |
| D2 | 도메인 | Cloudflare에 올릴 도메인 보유 여부(기존 도메인 서브도메인 사용 가능 여부) |
| D3 | 사람 로그인 | Cloudflare Access(구글 로그인, 코드 적음) / 앱 자체 구글 로그인 |
| D4 | 코드 배포 | git 유지(PC별 읽기 권한) / 허브 번들 배포 |
| D5 | 배정 | 요청자 PC 우선 / 공용 풀 / 혼합(가져오기=요청자, 렌더=풀) |
| D6 | 결과 보관 | 무기한 / N일 후 삭제 / N일 후 저렴한 등급 |
| D7 | 인원·라이선스 | 사내 제작 참여 인원 N, Remotion 라이선스 현황 |
| D8 | 텔레그램 | 허브에서 발송(키를 서버에) / 로컬 PC listener 유지 |
| D9 | 일러스트 정본 | 즉시 허브 정본 / 전환 기간 Drive 병행 |

---

## 9. 출처
- 코드: 이 리포 `CODEX_VIDEO_DESK/dashboard/server.py`·`remote_queue.py`·`RENDER_WORKER/worker.py`·`부사수PC_원클릭_셋업.bat`·`SETUP_FULL_PRODUCER.bat`·`shorts/run_codex_casual.bat` (2026-10-08 기준 줄번호)
- [AWS Lightsail 요금(공식)](https://aws.amazon.com/lightsail/pricing/) — Linux IPv4 번들 $5(0.5GB)/$7(1GB)/$12(2GB), 스냅샷 $0.05/GB·월
- [Cloudflare R2 요금(공식)](https://developers.cloudflare.com/r2/pricing/) — 무료 10GB·월, $0.015/GB·월, 송신 무료
- [Cloudflare One 계정 한도(공식)](https://developers.cloudflare.com/cloudflare-one/account-limits/) — Access 서비스 토큰 50, Tunnel 계정당 1,000
- [Cloudflare Teams 플랜 발표(2020 블로그)](https://blog.cloudflare.com/teams-plans) · [Costbench Zero Trust 무료 플랜](https://costbench.com/software/business-vpn/cloudflare-zero-trust/free-plan/) — 무료 50명(공식 최신 페이지 수치 미확인)
- [GCP 무료 등급 정리(wikidocs)](https://wikidocs.net/blog/@insightbridge/18254/) — e2-micro 무료는 미국 3개 리전(공식 미확인)
- [Remotion 라이선스(GitHub)](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md) · [Remotion 요금](https://www.remotion.dev/docs/license/pricing) — 원문 직접 열람 실패, 검색 인용
