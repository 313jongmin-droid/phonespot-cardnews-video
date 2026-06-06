# 자동화 매커니즘 개요 (★ 2026-06-04 기준)

> 이 폴더 시스템이 어떻게 동작하는가 — webui · telegram listener · outbox watcher · run_pngs · render flow.
> 다른 클로드 세션·코덱스 task 가 매커니즘 이해할 때 단일 진입점.

---

## 1. 전체 매커니즘 다이어그램

```
                ┌──────────────────────────────────────┐
                │     사장님 폰 (텔레그램·SNS)         │
                └──────────────┬───────────────────────┘
                               │
              ↓ "신규 수집"     │     ↑ outbox 자동 푸시
              ┌────────────────┴───────────────┐
              │   automation/scripts/          │
              │   telegram_listener.py         │ ← long polling
              │   (PC daemon, 항상 실행)       │
              └──┬─────────────────────────────┘
                 │ 명령 수신 → 클립보드 + Claude 앱 자동 실행 + Ctrl+V+Enter
                 ↓
              ┌────────────────────────────┐
              │  Cowork (Claude 데스크)    │  ← 클로드 세션
              │  - 가이드 일괄 Read        │
              │  - WebSearch 4 라인 병렬   │
              │  - 풀 후보 표 생성         │
              │  - JSON·prompt.md 작성     │
              └──┬─────────────────────────┘
                 │ _state/outbox/<file>.txt 떨굼
                 ↓
              ┌────────────────────────────┐
              │  telegram_listener.py      │
              │  outbox watcher (≤30초)    │ → 폰 도착
              └────────────────────────────┘

   별도 흐름:
              ┌────────────────────────────┐
              │  cardnews/webui/app.py     │ Flask + SSE
              │  http://localhost:5000     │
              └──┬─────────────────────────┘
                 │ "렌더" 클릭
                 ↓
              ┌────────────────────────────┐
              │  cardnews/scripts/         │
              │  run_windows.py            │ → Playwright HTML→JPG
              │  + captions.md 생성        │ → 18 JPG 저장
              └────────────────────────────┘
```

---

## 2. 컴포넌트별 책임

### 2-1. `automation/scripts/telegram_listener.py`

- **목적**: 폰 → PC 명령 전달 + 클로드 자동 실행 + outbox 자동 송신
- **실행**: `automation/start_telegram_listener.bat` (또는 silent `start_listener_silent.vbs`)
- **부팅 자동 시작**: `shell:startup` 폴더에 silent .vbs 바로가기 (수동 설치)
- **종속**: `_secrets/telegram_token.txt` + `_secrets/telegram_chat_id.txt` + `_secrets/listener_config.json` (mode/aumid)
- **두 가지 기능**:
  1. **수신 (사장님 → PC)**:
     - long polling `getUpdates` (35초 timeout)
     - 명령 매칭 (`신규 수집`, `news`, `scam` 등) → 클립보드 복사 + Claude 앱 (UWP AUMID `Claude_pzs8sxrjxfjjc!Claude`) 실행 + AppActivate + pyautogui Ctrl+V+Enter
  2. **송신 (PC → 사장님)** (★ outbox watcher):
     - 매 폴 사이클 끝에 `_state/outbox/*.txt` 검사
     - 새 파일 → 텔레그램 sendMessage 호출 (4096자 초과 시 3800자 청크 분할)
     - 송신 성공 시 `_state/outbox_sent/` 로 이동 (실패 시 outbox 잔존, 다음 사이클 재시도)
     - 응답 body 로그 (`resp_ok / message_id / desc`)

### 2-2. `automation/scripts/tg_send.py`

- **목적**: listener 없이 1회 송신용 헬퍼
- **사용**:
  - 모듈: `from tg_send import send_text; send_text("msg")`
  - CLI: `py -3 automation/scripts/tg_send.py <txt_path>`
- **종속**: `_secrets/telegram_token.txt` + `telegram_chat_id.txt` 자동 로드

### 2-3. `cardnews/webui/app.py` (Flask Phase 2)

- **목적**: 카드뉴스 렌더·결과 확인 컨트롤 패널
- **실행**: `cardnews/webui/start.bat` 또는 `py -3 cardnews/webui/app.py`
- **포트**: 5000
- **Basic Auth** (선택): `_secrets/webui_auth.txt` 존재 시 `user:pass` 1줄
- **기능**:
  - 슬러그 목록 + 상태 (done/ready/waiting)
  - 단일 슬러그 상세 (prompt.md 미리보기 + 이미지 업로드 + 렌더 트리거)
  - 실시간 렌더 로그 (SSE)
  - 결과 페이지 (18 JPG 그리드 + 사이즈별 탭 + ZIP 다운로드)
- **상태 판정**:
  - `done`: output/ 안 card_*.jpg 18장 + captions.md + 모든 JPG ≥ 30KB
  - `ready`: images/<slug>/ 안 1~5.png 모두 있음, 아직 렌더 X
  - `waiting`: 이미지 부족

### 2-4. `cardnews/run_pngs.bat` (CLI 렌더)

- **모드**: 셀렉트 (NNN 입력) 또는 number arg
- **흐름**:
  1. articles/ 에서 슬러그 목록 표시
  2. 사용자 NNN 입력 (콤마·공백 구분 다중)
  3. 각 슬러그마다:
     - 사전 검증 (prompt.md 존재 / 1~5.png 5장 / captions_md + cards 필드)
     - Playwright HTML→JPG 렌더 (1080/720/480 × 6장 = 18장)
     - captions.md 생성 (captions_md 채널 1~5 + narration_md 채널 6 자동 append)
     - manifest.json 생성
  4. 결과 요약 (성공·실패 리스트)
  5. 다시 셀렉트 루프 (사용자 빠져나갈 때까지)

### 2-5. `cardnews/scripts/` (렌더 엔진)

- `run_windows.py`: Playwright 부트스트랩 + HTML 템플릿 렌더링
- 폰트 로컬 임베드 (Pretendard `@font-face` + `file://`)
- 18 JPG 생성 후 자동 검증

---

## 3. 데이터 흐름 (단일 카드뉴스 1건)

| 단계 | 파일 | 작성자 |
|---|---|---|
| 1. articles JSON | `cardnews/articles/<slug>.json` | 클로드 (Write) |
| 2. prompt.md | `cardnews/images/<slug>/prompt.md` | 클로드 (Write) |
| 3. 1~5.png | `cardnews/images/<slug>/1~5.png` | 사장님 (GPT/Gemini 생성 후 업로드) |
| 4. 18 JPG + captions.md | `cardnews/output/<slug>/...` | run_pngs.bat (자동) |
| 5. SNS 업로드 | 외부 (네이버·인스타·유튜브·틱톡) | 사장님 |

---

## 4. outbox 자동 송신 규약 (클로드 → 사장님 폰)

### 4-1. 떨굼 위치

`_state/outbox/<YYYY-MM-DD>_<주제>.txt`

예시:
- `2026-06-04_collect_numbered.txt` (신규 수집 후보)
- `016_017_018_ready.txt` (작성 완료 통지)
- `ping_test.txt` (진단용)

### 4-2. 떨굼 내용 표준 (신규 수집)

```
[신규 수집 결과 YYYY-MM-DD]
D-7 기준: YYYY-MM-DD / 다음 번호: NNN~

==[ news ]==
1 토픽 — 발행일/D-N/매장정합/비고
2 ...
...

==[ scam ]==
N ...

==[ tip ]==
N ...

==[ qa ]==
N ...

[정직한 한계]
- ...

[선택 안내]
숫자만 회신 (예: 10 / 10+27 / 13,26,30)
```

### 4-3. 떨굼 내용 표준 (작성 완료)

```
[NNN 작성 완료]
slug: NNN_<type>_<topic>
title: ...
publication_date: YYYY.MM.DD

산출물:
- articles/<slug>.json
- images/<slug>/prompt.md

다음 단계 (사장님):
1. GPT/Gemini에 prompt.md 던져 1~5.png 생성
2. images/<slug>/ 에 업로드
3. webui 또는 run_pngs.bat 렌더
```

### 4-4. 4096자 처리

- listener가 자동으로 3800자 청크 분할 + `[1/N]` 프리픽스 추가
- 클로드는 분할 신경 X. 큰 텍스트 그대로 떨궈도 됨

---

## 5. 디버깅 진단 패턴

### 5-1. 텔레그램 안 옴

1. `_state/outbox/` 확인 — 파일 잔존 = listener 죽음
2. `automation/_state/listener_log.txt` 확인 — 마지막 줄에 `^C` = 사용자 중단
3. listener 재시작: `automation/start_telegram_listener.bat`
4. 즉시 1회 송신: `py -3 automation/scripts/tg_send.py <txt_path>`

### 5-2. webui 안 뜸

1. 포트 5000 점유 확인 (`netstat -ano | findstr 5000`)
2. `_secrets/webui_auth.txt` 형식 (`user:pass`)
3. Python 의존성: Flask 설치 여부
4. articles/ 디렉터리 권한

### 5-3. 렌더 실패

1. prompt.md 존재 + 5.png 존재 (사전 검증 통과)
2. captions_md + cards 필드 JSON 파싱 가능
3. Playwright 브라우저 (Chromium) 설치
4. 폰트 (Pretendard) 로컬 경로 + `@font-face` 정상

---

## 6. 보안·암묵 룰

- `_secrets/` 폴더 .gitignore 보호 (토큰·키 절대 외부 노출 ❌)
- `.bat` 파일 ASCII only + CRLF (한글·LF ❌, 매뉴얼 33~40 라인)
- JSON Edit 큰 필드 부분 수정 ❌ (Write 전체 박기)
- 매장 회피 키워드 자동 인지 + 회피
- "안양" 단어 모든 산출물 0건

---

## 7. 부팅 자동 시작 (영구화)

| 컴포넌트 | 등록 위치 | 비고 |
|---|---|---|
| telegram_listener | `shell:startup` 에 `start_listener_silent.vbs` 바로가기 | 1회 셋업 후 영구 |
| webui | 자동 시작 X (필요 시 수동) | 휴면 가능 |
| Claude 데스크탑 | 자동 시작 X | 텔레그램 트리거 시 listener 가 자동 실행 |

---

## 8. 다른 task와 매커니즘 공유

### 8-1. CODEX_VIDEO_DESK (영상 task)

- 별도 디렉터리 (`CODEX_VIDEO_DESK/`) + 자체 dashboard (`server.py` 포트 4878)
- 텔레그램 송신 함수 (`telegram_send`) 동일 token + 동일 chat_id 사용
- 카드뉴스 articles/<slug>.json 의 narration_md 를 영상 빌드 인풋으로 활용 가능
- 변경 시 영향 점검 항목:
  - articles JSON 스키마 변경 → 영상 task 인풋 호환성
  - 텔레그램 chat_id·token 변경 → 양쪽 모두 영향
  - outbox 폴더 위치 변경 → listener·tg_send 동기 점검

### 8-2. shorts (Remotion 기반)

- `shorts/` 디렉터리 + Remotion 컴포넌트
- 영상 task 와 별개의 빌드 (Node.js)
- 카드뉴스 18 JPG + narration_md 의 음성 합성 결과를 합쳐 60초 영상

### 8-3. 매뉴얼 (`_docs/INSTRUCTIONS_CARDNEWS.md`)

- 시스템 룰·자동화 룰·후보 수집·발행 룰 마스터 (1500줄+)
- 본 매뉴얼 헤더에 "본 CLAUDE.md 통해 진입" 명시 권장

---

## 9. 변경 이력

- 2026-06-04: 신설. 014~018 사이클 정착 매커니즘 종합.
