# 폰스팟 통합 컨트롤 패널 제안서

> **대상**: 코덱스 검토·구현
> **작성일**: 2026-06-03
> **상태**: 제안 (사장님 승인 대기)
> **목표**: 카드뉴스 + 영상 렌더 + 자산 관리 + 발행 패키지를 **1 페이지 1 포트**에서 통제

---

## 0. Executive Summary (사장님용 1분 요약)

현재 두 시스템 병존:
- **CODEX_VIDEO_DESK/dashboard** (포트 4877, 영상 워크플로)
- **cardnews/webui** (포트 8080, 카드뉴스 워크플로, Flask 기반 prototype)

→ 사장님·직원이 카드뉴스 → 영상 흐름에서 양쪽 dashboard 사이를 수동 이동해야 함. 통합 부재.

**제안**: **포트 4877 단일 dashboard로 통합**. 카드뉴스 기능을 코덱스 server.py에 흡수. cardnews/webui (Flask) 폐기. 사장님·직원은 한 URL만 기억 (`http://localhost:4877/`).

**투입 추정**: 코덱스 8~12h. 사장님 검수 1h.
**기대 효과**: 워크플로 1 페이지 완결 / Flask 의존성 제거 / 직원 진입 장벽 ↓

---

## 1. 현재 상태 (As-Is)

### 1.1 CODEX_VIDEO_DESK/dashboard (포트 4877)
- 기술: Python stdlib `http.server.ThreadingHTTPServer`
- 진입: `00_OPEN_CONTROL_PANEL.bat` → `python dashboard\server.py` → 자동 `webbrowser.open`
- 도메인: 영상 빌드 (shorts 폴더 기반)
- 작업 추적: 글로벌 `JOB` dict + `STATE_LOCK` (단일 job 직렬화)
- 27개 매크로 .bat (00~27)이 영상 워크플로 단계별 분리

### 1.2 cardnews/webui (포트 8080)
- 기술: Flask + Tailwind CDN
- 진입: `webui\start.bat` (수동 브라우저)
- 도메인: 카드뉴스 (articles/images/output)
- 기능: 슬러그 목록 / 상세 / 이미지 업로드 / 렌더 SSE / 결과 ZIP / 검색·필터 / Basic Auth
- 라우트 8개, 템플릿 3개 (index/slug/result)

### 1.3 두 시스템의 공통 분모
| 항목 | 코덱스 | webui |
|---|---|---|
| 슬러그 개념 | 영상 슬러그 | `NNN_<type>_<topic>` |
| 작업 트리거 | .bat 매크로 + endpoint | Flask route |
| 결과 폴더 | shorts/out · upload | cardnews/output |
| 로그 | `JOB["log"]` 누적 | SSE stream |

→ **개념은 같음, 구현만 분리**. 통합 자연스러움.

---

## 2. 통합 아키텍처 (To-Be)

### 2.1 단일 포트 · 단일 진입
- 포트 **4877** 유지 (코덱스 기존 + 사장님 기억된 주소)
- 진입: `00_OPEN_CONTROL_PANEL.bat` 그대로 (사장님·직원 기존 동선 유지)
- 자동 `webbrowser.open` 유지

### 2.2 기술 스택
- 기존: Python stdlib `http.server` (코덱스 패턴 유지)
- 추가 의존성 없음 (Flask 폐기 → 의존성 0)
- 템플릿 엔진: 단순 string 치환 또는 stdlib `string.Template`
- 정적 자산: dashboard/static/ (Tailwind CDN은 유지 가능)

### 2.3 도메인 분리 (탭 또는 사이드바)
```
┌─────────────────────────────────────────────────┐
│  Phonespot Control Panel                        │
│  [카드뉴스] [영상] [자산] [발행] [유지보수]      │
├─────────────────────────────────────────────────┤
│                                                 │
│  (선택된 탭의 콘텐츠)                            │
│                                                 │
└─────────────────────────────────────────────────┘
```

각 탭 = 독립 페이지 또는 SPA 라우팅 (선택). 권장은 멀티페이지 + 사이드바 (검색엔진 친화·즐겨찾기 OK).

---

## 3. 화면 구성 (와이어프레임)

### 3.1 메인 (`/`)
**대시보드 — 전체 상태 한눈에**
- 카드뉴스: 전체 N건 / 완료 N / 렌더 준비 N / 대기 N
- 영상: 빌드 완료 N / 진행 중 N / 대기 N
- 발행: 업로드 대기 N / 발행 완료 N (월별)
- 진행 중 작업 (JOB 상태) 라이브 표시

### 3.2 카드뉴스 (`/cardnews`)
- 슬러그 카드 그리드 (현재 webui 와 동일)
- 검색·필터 (상태·타입·기간)
- 각 카드 → `/cardnews/<slug>` 상세

### 3.3 카드뉴스 상세 (`/cardnews/<slug>`)
- 카드 6장 미리보기
- prompt.md 복사 버튼
- 이미지 드래그&드롭 업로드
- **[렌더링 시작]** 버튼 → 실시간 로그 (SSE 또는 JOB polling)
- 완료 후 → **[영상 빌드로 보내기]** 버튼 (해당 슬러그를 영상 워크플로 자동 전달)

### 3.4 영상 (`/video`)
- 27개 매크로 .bat을 카테고리로 묶어 표시 (현재 코덱스 패널 그대로)
- 카드뉴스에서 보낸 슬러그 자동 highlight
- 빌드 → SSE 로그 → 결과 mp4 미리보기

### 3.5 자산 (`/assets`)
- 일러스트 라이브러리 (ILLUSTRATION_DROP)
- 폰트·로고
- 시각 자산 검색·태그

### 3.6 발행 (`/publish`)
- upload/ 폴더 패키지 목록
- mp4 + caption.md + 썸네일 한 묶음
- SNS 채널별 미리보기 (블로그·인스타·스레드·유튜브·틱톡)

### 3.7 유지보수 (`/maintenance`)
- 27 매크로 중 백업·롤백·정리 분류
- 시스템 상태·로그·디스크 사용량

---

## 4. 카드뉴스 기능 명세 (webui 흡수)

코덱스가 새로 만들 영역. cardnews/webui/app.py·templates의 모든 기능을 코덱스 server.py 패턴으로 재구현.

### 4.1 라우트 매핑 (Flask → stdlib)

| 기능 | 옛 (Flask) | 신 (stdlib) |
|---|---|---|
| 슬러그 목록 | `GET /` | `GET /cardnews` |
| 상세 | `GET /slug/<id>` | `GET /cardnews/<slug>` |
| 이미지 업로드 | `POST /slug/<id>/upload` | `POST /api/cardnews/<slug>/upload` |
| 렌더 SSE | `GET /slug/<id>/render-stream` | `GET /api/cardnews/<slug>/render-stream` (또는 JOB polling) |
| 결과 페이지 | `GET /result/<id>` | `GET /cardnews/<slug>/result` |
| 결과 ZIP | `GET /result/<id>/zip` | `GET /api/cardnews/<slug>/zip` |
| 정적 (output) | `GET /output/<id>/<f>` | `GET /static/cardnews/<slug>/<f>` |
| 정적 (images) | `GET /images/<id>/<f>` | `GET /static/cardnews/images/<slug>/<f>` |

### 4.2 핵심 헬퍼 (재사용 가능)
- `_is_done(slug)` — 18 jpg + captions.md + 각 jpg > 30KB
- `_img_count(slug)` — 업로드 이미지 카운트
- `_list_slugs(filter_q, filter_status)` — 슬러그 목록 + 필터

→ cardnews/webui/app.py의 56~95줄 그대로 이식 가능.

### 4.3 렌더 호출
- 코덱스 기존 `run_job(name, commands, cwd)` 패턴 재사용
- 카드뉴스 렌더 = `run_job("cardnews:003", [['py', '-u', 'scripts/run_windows.py', '003']], cwd=cardnews/)`
- JOB 상태는 SSE 대신 `GET /api/job` polling으로 단순화 가능 (코덱스 기존 방식)

### 4.4 카드뉴스 → 영상 자동 연결 (핵심 통합 가치)
- 카드뉴스 렌더 완료 시 자동으로 영상 작업 후보에 추가
- 카드뉴스 상세 페이지에 `[영상 빌드 시작]` 버튼
- 클릭 시 코덱스 영상 워크플로의 적절한 .bat (예: `02_IMPORT_DOWNLOADS_AND_RENDER.bat`) 호출

---

## 5. 데이터 모델·폴더 구조 (변경 없음)

```
phonespot_cardnews/
├── cardnews/                  (그대로 유지)
│   ├── articles/NNN_*.json
│   ├── images/NNN_*/
│   ├── output/NNN_*/
│   └── scripts/run_windows.py
├── shorts/                    (그대로 유지)
│   ├── articles/ images/ out/
│   └── scripts/
├── CODEX_VIDEO_DESK/          (그대로 유지)
│   ├── dashboard/server.py   ← 여기에 카드뉴스 라우트 흡수
│   └── 00~27 .bat
├── upload/                    (발행 패키지)
└── _docs/
    └── PROPOSAL_UNIFIED_DASHBOARD.md (이 문서)
```

**폴더 이동 없음**. 코덱스 server.py만 확장. cardnews/webui/ 폐기 (참조용 유지 또는 삭제).

---

## 6. API 엔드포인트 (전체)

### 6.1 공통
- `GET /` — 메인 대시보드
- `GET /api/health` — 헬스 체크
- `GET /api/job` — 현재 JOB 상태 (코덱스 기존)
- `POST /api/job/cancel` — 진행 중 작업 취소

### 6.2 카드뉴스 (신규)
- `GET /cardnews` — 슬러그 목록 (HTML)
- `GET /cardnews/<slug>` — 상세 (HTML)
- `GET /cardnews/<slug>/result` — 결과 (HTML)
- `POST /api/cardnews/<slug>/upload` — 이미지 업로드 (multipart)
- `POST /api/cardnews/<slug>/render` — 렌더 트리거 (JOB 등록)
- `GET /api/cardnews/<slug>/zip` — 결과 ZIP
- `GET /static/cardnews/<slug>/<f>` — 결과 파일
- `GET /static/cardnews/images/<slug>/<f>` — 업로드 이미지

### 6.3 영상 (코덱스 기존)
- 27개 .bat 매크로 라우트 (코덱스 기존 그대로)

### 6.4 자산 (신규 또는 기존 확장)
- `GET /assets` — 일러스트 라이브러리
- `POST /api/assets/upload` — 새 일러스트 업로드

### 6.5 발행 (신규)
- `GET /publish` — 패키지 목록
- `GET /publish/<slug>` — 패키지 상세

---

## 7. 통합 시 보존 사항 (사장님 의사결정 기록)

### 7.1 코덱스 기존 자산 100% 유지
- 27개 매크로 .bat — 변경 없음
- `dashboard/server.py` 기존 JOB·run_job 패턴 — 변경 없음
- ILLUSTRATION_DROP 폴더 — 변경 없음
- BACKUPS 정책 — 변경 없음

### 7.2 cardnews/webui 처리
- **권장**: 폐기 (참조용 README 1줄만 남기고 폴더 삭제)
- **대안**: archive 폴더로 이동 (참조 가능)

### 7.3 카드뉴스 코어 (scripts/, articles/, images/, output/) 보존
- 통합 dashboard는 이들을 호출만. 폴더 구조·룰 변경 0
- `_docs/INSTRUCTIONS_CARDNEWS.md` 룰 그대로 유효

---

## 8. 보안·접근 제어

### 8.1 LAN 공유 (기본)
- 0.0.0.0:4877 바인드 (코덱스 기존)
- 윈도우 방화벽 4877 inbound 1회 허용
- 직원 PC·모바일: `http://192.168.x.x:4877/`

### 8.2 Basic Auth (선택)
- cardnews/webui 패턴 그대로: `_secrets/dashboard_auth.txt` 1줄 `user:pass`
- 없으면 인증 비활성 (LAN only)
- 코덱스 기존 server.py에 미들웨어 추가 1곳

### 8.3 외부 노출 금지
- 본 dashboard는 LAN 전용. 인터넷 노출 ❌

---

## 9. 마이그레이션·이행 계획

### Phase A — 카드뉴스 흡수 (6~8h)
1. server.py에 `/cardnews/*` 라우트 8개 추가
2. cardnews/webui/templates/*.html 의 디자인을 코덱스 dashboard CSS·레이아웃에 맞춰 재작성
3. 헬퍼 함수 (`_is_done`, `_img_count`, `_list_slugs`) 이식
4. 카드뉴스 렌더 `run_job` 호출 wiring
5. 결과 페이지 + ZIP 다운로드

### Phase B — 메인 대시보드 (1~2h)
1. `GET /` 통합 대시보드 (전체 상태 요약)
2. 사이드바·탭 네비게이션
3. 진행 중 JOB 라이브 표시

### Phase C — 카드뉴스↔영상 연결 (1~2h)
1. 카드뉴스 상세에 `[영상 빌드]` 버튼
2. 클릭 시 슬러그를 영상 워크플로에 전달
3. 영상 dashboard에서 해당 슬러그 자동 highlight

### Phase D — 자산·발행 (선택, 2~4h)
1. 자산 라이브러리 페이지
2. 발행 패키지 페이지

### Phase E — 정리 (1h)
1. cardnews/webui/ 폐기 또는 archive
2. README 갱신
3. 매뉴얼 1줄 갱신 (`INSTRUCTIONS_CARDNEWS.md`)

**총 추정**: A+B+C 필수 = 8~12h. D 선택 +2~4h. E 1h.

---

## 10. 리스크·완화

| 리스크 | 영향 | 완화 |
|---|---|---|
| JOB lock 단일 직렬화 → 카드뉴스·영상 동시 불가 | 중 | 1) 작업 큐 도입 2) 또는 직렬 OK 정책 (현재 사장님 패턴이 직렬이라 큰 문제 아님) |
| stdlib 템플릿이 Flask 대비 손이 더 감 | 작 | string.Template 또는 jinja2 추가 (의존성 1개) |
| 카드뉴스 SSE 손실 | 중 | JOB polling (1초 간격)으로 대체 — 단순·안정 |
| 통합 후 디자인 일관성 | 중 | 코덱스 dashboard CSS·디자인 톤을 카드뉴스 페이지에 그대로 적용 |
| 코덱스 기존 .bat 충돌 | 낮 | 모든 카드뉴스 라우트는 `/cardnews/*` prefix로 namespace 분리 |

---

## 11. 검토 요청 사항 (코덱스에게)

1. 본 제안 **아키텍처 적정성** 검토 — stdlib 유지 vs jinja2 추가 vs 다른 옵션
2. **JOB lock 단일 직렬화** vs 큐 — 사장님 사용 패턴에 어느 쪽이 적합한지 의견
3. **카드뉴스 SSE vs polling** 선택 (현재 cardnews/webui SSE 동작 검증됨, 코덱스 패턴은 polling)
4. **Phase A 8h 견적 적정성** 검토
5. **카드뉴스 → 영상 연결**의 자연스러운 인터페이스 제안 (단순 버튼 vs 메타데이터 전달 vs 자동 트리거)
6. **참조 자료**: `cardnews/webui/app.py` 311줄 / `cardnews/webui/templates/*.html` 3개 → 코덱스가 흡수 시 그대로 차용 가능한 부분 식별

---

## 12. 결정 필요 (사장님)

- [ ] Phase A·B·C 진행 승인
- [ ] cardnews/webui 폐기 OK (참조용 archive로 보관)
- [ ] Phase D (자산·발행) 포함 여부
- [ ] Basic Auth 1단계 적용 여부

---

## 부록 A — cardnews/webui 핵심 로직 인용 (이식 참조용)

### A.1 `_is_done(slug)` — 완료 판정
```python
def _is_done(slug):
    out = OUTPUT_DIR / slug
    if not out.exists():
        return False
    jpgs = list(out.rglob('card_*.jpg'))
    if len(jpgs) < 18:
        return False
    if not (out / 'captions.md').exists():
        return False
    if any(p.stat().st_size < 30 * 1024 for p in jpgs):
        return False
    return True
```

### A.2 슬러그 목록 + 필터
```python
def _list_slugs(filter_q=None, filter_status=None):
    for jf in sorted(ARTICLES_DIR.glob('*.json')):
        slug = jf.stem
        data = json.loads(jf.read_text(encoding='utf-8'))
        done = _is_done(slug)
        nimg = _img_count(slug)
        status = 'done' if done else ('ready' if nimg >= 5 else 'waiting')
        # ... 필터링 후 append
```

### A.3 렌더 SSE → coding 패턴 (참고 — polling으로 대체 가능)
```python
proc = subprocess.Popen(
    [sys.executable, '-u', 'scripts/run_windows.py', prefix],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, bufsize=1, env={**os.environ, 'PYTHONUNBUFFERED': '1'},
)
for line in iter(proc.stdout.readline, ''):
    yield f"data: {line.rstrip()}\n\n"
```

---

## 부록 B — 파일 변경 요약 (예상)

| 파일 | 변경 |
|---|---|
| `CODEX_VIDEO_DESK/dashboard/server.py` | +500~700 줄 (카드뉴스 라우트·헬퍼·JOB 통합) |
| `CODEX_VIDEO_DESK/dashboard/templates/*.html` (신규) | +400~600 줄 (cardnews 페이지 3개 + 메인 대시보드) |
| `CODEX_VIDEO_DESK/dashboard/static/*.css` (선택) | +100 줄 |
| `cardnews/webui/` | 폐기 또는 archive 이동 |
| `_docs/INSTRUCTIONS_CARDNEWS.md` | 1줄 갱신 (`run_pngs.bat` 외 `localhost:4877` 안내 추가) |

---

**문서 끝**. 코덱스 검토 결과·견적·의견 회신 부탁드립니다.
