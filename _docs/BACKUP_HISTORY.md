# 폰스팟 카드뉴스 자동화 - 백업 문서 (BACKUP)

> 이 문서를 읽으면 어떤 시점에서든 동일한 시스템을 처음부터 100% 복원할 수 있다.
> 컨텍스트가 날아가거나 코드가 손상됐을 때 복구용으로 사용.

## 야간 자동화 아키텍처 (2026.05.28) — Path B + 채팅 전략 B

### 결정된 구조
**Path B · 반자동 절충** (Cowork+미니PC 분업)
- **아침 (사장님 수동)**: Cowork에서 신규 뉴스 수집 → 토픽 선택 → JSON 작성 → `images/<slug>/` 빈 폴더 생성
- **02:00 자동** (미니 PC `night_daemon.py`):
  1. articles 스캔, `images/<slug>/` 존재 + 이미지 0장 + output 미완성인 슬러그 = 처리 대상
  2. Chrome 자동화로 ChatGPT 이미지 생성 (Day 3에서 구현)
  3. `run_all.bat` 자동 실행
  4. 진행 상황·결과 텔레그램 단방향 알림

### Cowork 샌드박스 제약 (중요)
- `api.telegram.org` 차단됨 (allowlist 정책. Chromium·Gemini API와 동일)
- Cowork 세션은 직접 텔레그램 송수신 불가
- 따라서 텔레그램 송수신·이미지 생성·렌더링 = **모두 미니 PC에서**

### Chrome 자동화 채팅 전략 = B (1 카드뉴스 = 1 새 채팅)
- 영원한 자동화 운영 고려 시 채팅 누적·컨텍스트 오염 회피
- 슬러그당 새 채팅 1개 생성 → 그 안에 5장 프롬프트 차례로 입력 → 5장 다운로드 → 다음 슬러그 = 또 새 채팅
- 1주일 약 5~7개 채팅 누적 (1 카드뉴스/일 가정)
- 운영하면서 결과 보고 1 카드뉴스 1 채팅 그대로 / 영구 1채팅 / 매 이미지 새 채팅 중 조정

### 구축 단계
- **Day 1 ✓** 텔레그램 alarm helper (`scripts/telegram_notify.py` + chat_id 셋업)
- **Day 2 ✓** 야간 daemon 골격 (`scripts/night_daemon.py` + `night_daemon.bat`)
- **Day 3** Chrome MCP/Playwright로 ChatGPT 이미지 자동 생성
- **Day 4** 렌더링 통합 (`run_all.bat` 호출) + 최종 알림
- **Day 5+** 운영 안정화

### 파일
- `scripts/telegram_notify.py` (123줄, 표준 라이브러리)
- `scripts/night_daemon.py` (123줄)
- `night_daemon.bat` (Task Scheduler용 wrapper)
- `telegram_token.txt` (.gitignore 보호)
- `telegram_chat_id.txt` (.gitignore 보호)

### Task Scheduler
매일 02:00 → `night_daemon.bat` 실행. 미니 PC 절전·슬립 끄기 필수.

---

## PROJECT_INSTRUCTIONS 다이어트 (2026.05.26)

토큰 절약 목적으로 PROJECT_INSTRUCTIONS.md를 활성 룰만 남기고 슬림화.
- 22,343 bytes (431줄) → 6,127 bytes (128줄), 72.6% 감소
- 추정 절감: 약 4,000~5,400 토큰/세션
- 동작 보존: 카드뉴스 생성 흐름·디자인 시스템·캡션 규칙 모두 그대로

### 다이어트로 PROJECT_INSTRUCTIONS에서 제거된 항목 (이력 보존용)
모두 PROJECT_INSTRUCTIONS.md.backup_pre_diet 파일에 통째 보존.

- **v3 이미지 프롬프트 전문** (Editorial documentary photography... 약 50줄) — 현재 v6 활성
- **v3 핵심 원칙** (NYT Tech/Wired 톤 등) — v6에 흡수됨
- **표지 스타일 4종 가이드** (A1 magazine / A2 fullscreen_band / A3 typography / A4 image_overlay) — v8 매거진 통일 모드 이후 1종만 사용
- **디자인 라이브러리 v1 (P1~P10 본문 패턴)** — v8 매거진 통일 후 미사용
- **4-A 카드 영역 인라인 체크리스트** — articles JSON 자동 로드로 대체됨
- **4-C grep 검증 룰** — run_windows.py 자동 검증으로 대체됨
- **v2 업그레이드 디자인** (블록 그라데이션·드롭 그림자·인사이트 박스 등) — v8 매거진에서 미사용
- **wkhtmltoimage 호환성 주의** — Playwright/Chromium 전환 후 무관
- **각종 사용 예시 코드** — 옛 패턴

### PROJECT_INSTRUCTIONS에 새로 추가된 룰
- **토큰 절약 룰** 5개 (WebSearch ≤2회 / 긴 산출물 채팅 미출력 / 응답 짧게 / Sources 조건부 / 재 Read 금지)
- **매장 비즈니스 모델** 명시 (고가 단말+고가 요금제 / 회피·선호 토픽 룰)

---

## 이미지 프롬프트 v6.1 (2026.05.27) — 자기완결 블록 양식

v6 유지 + 양식 변경:
- **각 카드 프롬프트가 자기완결**(공통 룰 매 블록에 박음) → 5장 일괄/개별 복붙 모두 동일 퀄리티
- 첫 줄: 카드 식별 (`■ N.png — 헤드라인 핵심`)
- 둘째 줄: 공통 기술 룰 한 줄 압축
- 셋째 줄: 본문 직역 구체 장면 1~2문장
- 시리즈 통일 지시("Same tone as image 1") 명시적 금지

---

## 이미지 프롬프트 v6 (2026.05.26) — 카드별 독립 + 구체 장면 직역

사용자 피드백: 갤럭시 AI 구독클럽(5/26 작성, slug=galaxy_ai_club_may_2026)의 5장 프롬프트가 가장 좋았다. 그 스타일을 디폴트로 고정.

### v5 → v6 변경 (1가지 추가)
- **각 카드는 완전히 독립적** — 5장 색감·톤·소품·환경 통일 금지. 시리즈 일관성 신경 X. 각 카드가 자기 본문 직역에만 충실.
- **구체 장면(scene)으로 직역** — "어떤 손이 무엇을 하는지", "어떤 소품이 어디에 있는지" 1~2문장으로 묘사. 추상 상징 대신 실제 장면.
- 레퍼런스: galaxy_ai_club_may_2026 (달력+마커 / 손+봉투 / 폰 라인업 flat lay / ATM 투입 / 플래너+플래그).

### v5에서 유지
- 카드 본문 내용 직역 (방향 1) / 밝은 톤 (검정 배경·드라마틱 조명 ❌) / 숫자·문자 소품 흐림 / NO faces/logos/text overlay.

---

## 이미지 프롬프트 v5 (2026.05.22) — 카드별 내용 일치 + 밝은 톤

v4를 대체. 상세 규칙은 PROJECT_INSTRUCTIONS.md Step 3 참조.

### v4 → v5 변경 (2가지)
1. **카드별 내용 일치 (방향 1)** — 각 이미지는 그 카드 본문이 실제로 말하는 내용을 직접 그림.
   - 막연한 은유(리본·자물쇠·동전더미) 금지. 범용 "매장 분위기" 5장 돌려쓰기 금지.
   - 추상 개념 카드는 직결 소품으로 직역: 법 변화=서류+화살표 / 가격 하락=가격표 계단 / 조건 확인=계약서+돋보기 / 금액 비교=높이차 배치.
   - 판단: "사진만 보고 카드 주제가 떠오르는가" → YES여야 함.
2. **밝은 톤** — 배경 soft warm white #F5F0E8 / light cream. charcoal·black은 폰 본체 등 작은 피사체만.
   - bright airy daylight, 부드러운 그림자. 드라마틱 스포트라이트·검정 배경 금지.
   - 카드 하단 검정 그라데이션이 가독성 담당하므로 원본 밝아도 OK. 카드 6(흰 배경)과 톤 통일.

### 유지 (v4에서)
- 5장 앵글·구도 다양화 / 공통 통일은 컬러·조명만 / orange #F74B0B 포인트 소량 / 숫자·문자 소품은 흐림 처리.

---

## v8 주요 변경사항 (2026.05.11 후반) — 매거진 통일 톤 + 5장 다양화 이미지

### 카드뉴스 구조 변경
- **카드 1~5: 이미지 + 검정 그라데이션 + 흰 텍스트** (매거진 통일 톤)
- **카드 6: 흰 배경 + 폰스팟 로고** (CTA 차별)
- articles/<slug>.json의 `cards` 배열에서 카드별 데이터 자동 로드
- 이미지: `images/<slug>/card_1.png ~ card_5.png` (5장만)
- auto-rename: 폴더에 5장 드롭하면 mtime 순서로 자동 매핑

### 이미지 프롬프트 v4 — 매거진 5장 다양화
- 5장 시리즈 통일 = 시각 정보 반복 = 밋밋함 → **카드별 시각 콘셉트 의도적 다양화**
- 환경·앵글·구도 각기 다르게 (공통은 컬러 톤/조명만)
- 콘텐츠 의미 ↔ 시각 매칭 표 PROJECT_INSTRUCTIONS.md Step 3 참조
- 누끼 5장 반복 금지 / 매장 윈도우 5장 반복 금지

### 본문 카드 톤 (v7 newsroom 유지)
- 검정 배경 + 큰 흰 헤드라인 + 옅은 흰 본문
- 헤드라인은 명사형, 본문은 서술어 완성된 문장
- 키워드 1곳에 오렌지 강조 (`<span class="hl">`)
- 폰트 +2pt (head 60→62, body 26→28, source 18→20)
- "원UI" → "ONE UI" 표기

### 카드 6 변경
- 배경: 흰색 단색 (radial-gradient 검정 X)
- 메인 시각: 큰 폰스팟 로고 (logo_color_trimmed.png)
- 텍스트 색상 자동 반전 (.card6-mode CSS)

### 자동 렌더 모드 전환
- `USE_MAGAZINE_MODE` 자동 감지 (articles JSON에 cards 필드 있으면 ON)
- ON: 6장 모두 `render_card_magazine()` 사용
- OFF: 기존 render_card_1~6 (구버전 호환)

---

## v7 주요 변경사항 (2026.05.11 오전) — Newsroom 톤 전환

광고 톤 → 뉴스 매체 톤으로 디자인 시스템 전반 정돈.

### 카드 1 — A4 image_overlay 추가 (현재 디폴트)
- 이미지 풀스크린 + 상하단 미세 검정 그라데이션 + 텍스트 직접 오버레이
- kicker (빨간 점 + 한글) + 단일 헤드라인 + deck + by-line (매체+날짜)
- CARD1_DATA에 newsroom 필드 추가: kicker / headline / deck / publication / date

### 카드 6 — newsroom 톤 (거대 로고 X)
- 거대 폰스팟 로고 + "광교점에서 받으세요" CTA → 작은 로고 + 좌측 정렬 매장 정보 단락
- 형식: 헤드라인 → 본문 한 문장 → 작은 로고 → 매장 주소·KakaoTalk·링크 → 미세 구분선 + 안내 작은 텍스트

### 본문 카드 톤 미세 조정
- h2 letter-spacing -2.5 → -2 / line-height 1.18 → 1.2
- body-text font-weight 600 → 500 / line-height 1.65 → 1.7 (호흡)
- b/hl 강조 weight 900 → 800 (덜 외침)
- source weight 600 → 500
- page-ind 색 #94A3B8 → #CBD5E1 (배경처럼)

### 이미지 프롬프트 v3
- 광고 톤 키워드 차단 (coral-to-gold, theatrical lighting, gift boxes 등)
- "Editorial documentary photography for a tech news article" 톤 명시
- 참조: NYT Tech / Wired / Bloomberg Tech 톤
- 자세히는 PROJECT_INSTRUCTIONS.md Step 3 참조

---

## v6 변경사항 (2026.05.11 오전) — 디자인 라이브러리 도입

매번 같은 6장 구조로 인한 단조로움 해결. 표지 + 본문 패턴 다양화.

### 카드 1 표지 라이브러리 (4종)
- `magazine` (A1): 이미지 + 좌측 fade + 좌측 텍스트
- `fullscreen_band` (A2): 이미지 풀스크린 + 하단 오렌지 띠 (비추천 - 광고 톤)
- `typography` (A3): 이미지 X, 거대 타이포 + 좌측 컬러 블록
- `image_overlay` (A4) ⭐ v7 디폴트: 이미지 풀스크린 + 미세 그라데이션 + 텍스트 오버레이 (newsroom)

코드: `CARD1_DATA["style"]` 키로 선택. dispatcher 패턴.

### 본문 카드 패턴 함수 (P5~P7 신규)
- `pattern_big_num_2(size, h2, body, num1, label1, num2, label2, page_num)` — P5
- `pattern_compare_table(size, h2, body, col1_title, col2_title, rows, page_num)` — P6  
- `pattern_timeline(size, h2, body, steps, page_num)` — P7

기존 P1~P4·P10은 인라인 형태로 카드 함수 안에 직접 작성.

### 패턴 선택 룰
- 매 기사마다 다른 패턴 조합 (직전 기사 답습 금지)
- 카드 2 = P1 (리드) 고정
- 카드 3~5 = 콘텐츠에 맞는 패턴 매칭
- 카드 5 = 자유 디자인 원칙 (라이브러리 외도 OK)

자세한 매칭표는 PROJECT_INSTRUCTIONS.md Step 4 참조.

---

## v5 주요 변경사항 (2026.05.04)

| 변경 | 설명 |
|---|---|
| **JSON 부분 분리 (captions만)** | `articles/<slug>.json`의 `captions_md` 필드에 캡션 통째 저장 → renderer 자동 로드. 캡션 누락 사고 구조적 차단. |
| **카드 4도 자유 디자인 원칙** | STEP 박스 3개는 한 옵션일 뿐. 카드 5와 동일하게 콘텐츠에 맞춰 자유 |
| **자동 검증 스크립트** | `run_windows.py` 끝에 추가 — 카드 누락/크기 이상/이전 기사 잔재 자동 감지 |
| **백업 파일 자동 정리** | 최근 5개만 유지, 나머지 자동 삭제 |
| **기사 수집 룰 명확화** | D-3 0건 시 D-7 완화 (시즌성만), Chrome MCP 끊김 대처, 시즌성 캘린더 등 (PROJECT_INSTRUCTIONS.md Step 1 참조) |
| **이미지 프롬프트 v2** | 옵션 A 최종 — SUBJECT 3요소 (메인+컨텍스트+무드), COMPOSITION 우측 배치, subtle lighting. 카드 1 매거진 레이아웃과 호환 |
| **★ 영상 프로젝트 분리** | 카드뉴스 → 숏폼 영상 변환은 별도 Cowork 프로젝트로 운영. 같은 폴더 공유, 인스트럭션 분리. `PROJECT_INSTRUCTIONS_SHORTS.md` 참조 |

## 두 워크플로우 구조

```
phonespot_cardnews/  (공유 폴더, Cowork 프로젝트 2개)
│
├── 프로젝트 A: 카드뉴스 — PROJECT_INSTRUCTIONS.md
│   - scripts/cardnews_renderer_v2.py + run_windows.py
│   - 출력: output/<slug>/{1x1, 4x5, 9x16, captions.md}
│
└── 프로젝트 B: 숏폼 영상 — PROJECT_INSTRUCTIONS_SHORTS.md ★ NEW
    - scripts/shorts/generate_tts.py + generate_shorts.py
    - 입력: output/<slug>/9x16/* + articles/<slug>.json captions_md
    - 출력: output/<slug>/shorts.mp4
```

---

## 0. 빠른 시작 (이 시스템을 처음 보는 사람)

```
1. C:\Users\<USER>\Documents\phonespot_cardnews\ 폴더 확인
2. WINDOWS_SETUP.md 따라 의존성 설치 (Python, wkhtmltopdf 백업, 폰트는 자동)
3. 새 기사 작업 시:
   a. articles/<slug>.json 만들기 (선택, run_windows.py가 SLUG 자동 인식용)
   b. images/<slug>/cover.png 저장 (ChatGPT 등에서 생성)
   c. scripts/cardnews_renderer_v2.py 콘텐츠 변경 (카드 1~6 텍스트)
   d. run_pngs.bat 더블클릭 → 자동 실행 → 18장 JPG + captions.md 생성
```

---

## 1. 프로젝트 개요

**목적**: 매일 IT/통신 뉴스 1건 → 카드뉴스 18장 (1:1 / 4:5 / 9:16 × 6장) + SNS 캡션 5채널 자동 생성

**핵심 가치**:
- 수작업 시간 30~45분 → 5분 (자동화)
- 매일 발행 가능 (지속 운영)
- 폰스팟 광교점 마케팅 컨텐츠 (KT 공식 인증 대리점)

**브랜드**: 폰스팟 광교점 (휴대폰 성지, 시세비교 운영, KT 공식 인증 대리점)

---

## 2. 시스템 환경

**OS**: Windows 11
**Python**: 3.11+ (검증: 3.14.4)
**렌더링 엔진**: Playwright + Chromium (headless)
**폰트**: Pretendard (CDN 자동 로드)

**필수 설치**:
- Python (Microsoft Store 또는 python.org)
- wkhtmltopdf (백업용, 현재는 Playwright 사용. 추후 wkhtmltoimage 폴백 가능성 위해 유지)

**자동 설치 (run_windows.py 첫 실행 시)**:
- playwright (pip)
- chromium (playwright install chromium, 약 130MB, 첫 실행만)
- Pillow (자동 설치 코드 있지만 현재 미사용 — Playwright가 직접 JPG 출력)

---

## 3. 폴더 구조 (전체)

```
phonespot_cardnews/
├── README.md                           # 프로젝트 개요
├── SETUP_GUIDE.md                      # Cowork 이관 가이드
├── WINDOWS_SETUP.md                    # Windows 환경 세팅 가이드
├── PROJECT_INSTRUCTIONS.md             # Cowork 프로젝트 지침 (원본)
├── BACKUP.md                           # ★ 이 문서 (시스템 복구 마스터)
├── .gitignore
├── logo.jpg                            # 폰스팟 로고 (사각, 사용 안 함, 이전 버전 잔재)
├── run_pngs.bat                        # ★ 메인 실행 파일 (더블클릭)
├── run_log.txt                         # 자동 갱신되는 실행 로그
│
├── articles/                           # 기사별 JSON 콘텐츠 (run_windows.py SLUG 인식용)
│   ├── voice_phishing_care.json
│   └── face_auth_july.json
│
├── images/                             # 기사별 cover 이미지
│   ├── logo_cutout_original.png        # ★ 폰스팟 컬러 누끼 (카드 2~6 로고)
│   ├── logo_cutout_white.png           # 흰 누끼 (어두운 배경용 백업)
│   ├── voice_phishing_care/cover.png
│   └── face_auth_july/cover.png
│
├── output/                             # 결과물 (기사별 폴더)
│   ├── voice_phishing_care/
│   │   ├── 1x1/card_1~6.jpg
│   │   ├── 4x5/card_1~6.jpg
│   │   ├── 9x16/card_1~6.jpg
│   │   └── captions.md
│   └── face_auth_july/...
│
├── fonts/                              # Pretendard OTF (이전 시도 잔재, 현재는 CDN 사용. 삭제해도 무방)
│
├── scripts/
│   ├── cardnews_renderer_v2.py         # ★ 메인 렌더러 (수정 대상)
│   ├── cardnews_renderer_v2_backup_*.py # 이전 버전 백업 (iphone18, moto_g77, inline, wkhtml)
│   ├── run_windows.py                  # ★ Windows 런처 (SLUG 자동 인식 + Playwright)
│   └── generate_image.py               # Gemini API 이미지 생성 (선택, 현재는 ChatGPT 직접 생성)
│
├── samples/sample_iphone18*            # 참고용
└── templates/caption_template.md       # 참고용
```

---

## 4. 디자인 시스템 (모든 값)

### 4.1 색상 팔레트

| 용도 | 색상 코드 | 비고 |
|---|---|---|
| 메인 (오렌지) | `#F74B0B` | 폰스팟 브랜드 컬러, 모든 강조 |
| 검정 텍스트 | `#1A1A1A` | 헤드라인, 본문 |
| 흰색 배경 | `#FFFFFF` | 카드 기본 배경 |
| 회색 본문 (옅음) | `#64748B` | sub-cover, 부제 |
| 회색 페이지 인디케이터 | `#94A3B8` | source, page-ind |
| 회색 라이트 (스펙박스) | `#F8FAFC` | spec block 배경 |
| 어두운 박스 (워치/info) | `#1A1A1A` | Card 5 등 검정 박스 |

### 4.2 폰트 (Pretendard)

```css
font-family: "Pretendard", "Noto Sans KR", "Malgun Gothic", sans-serif;
```

**CDN 로드**:
```css
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');
```

**Weight**: 100, 300, 400, 500, 700, 900 (Pretendard 9종 중 사용)

**규칙**:
- 모든 텍스트 요소에 `font-family: ... !important;` 명시 (인라인 style 포함)
- `*` 셀렉터에 강제 적용 (GLOBAL_FONT_RESET)

### 4.3 사이즈 시스템 (3종)

| 사이즈 | 너비 | 높이 | 용도 |
|---|---|---|---|
| 1x1 | 1080 | 1080 | 인스타 피드, 페북 |
| 4x5 | 1080 | 1350 | 인스타 피드 (최대 점유) |
| 9x16 | 1080 | 1920 | 스토리, 릴스, 틱톡 |

### 4.4 카드 1: 매거진 표지 (모든 사이즈 디테일)

**구조**: 풀스크린 cover.png + 좌측 흰 페이드 + 좌측 하단 텍스트 + 우측 상단 라벨

**1x1 (1080x1080)**:
- cat_size: 22, head_size: 77, price_size: 110, sub_size: 26
- text_left: 80, text_bottom: 200
- cat_letter (자간): 4
- bg-img: 1080x1080 cover, object-position: center
- left-fade: 65% width, white gradient (0.95~0)

**4x5 (1080x1350)**:
- cat_size: 26, head_size: 91, price_size: 134, sub_size: 31
- text_left: 80, text_bottom: 280
- cat_letter: 5

**9x16 (1080x1920)** ★ 별도 레이아웃:
- 이미지를 카드 가운데 정렬 (1200x1200, 위/아래 360px 여백 균등)
- 좌우 cover (60px씩 자연스럽게 잘림)
- 좌측 fade 없음 (이미지/텍스트 영역 분리)
- cat_size: 38, head_size: 108, price_size: 168, sub_size: 38
- text_bottom: 130

**라벨 (우측 상단)**:
- top/right: 40 (1x1, 4x5) / 50 (9x16)
- font-size: cat_size, font-weight: 900
- letter-spacing: cat_letter, text-transform: uppercase
- white-space: nowrap, text-align: right
- 오렌지 도트: cat_size/2 width × cat_size/2 height, border-radius 50%

**카테고리 (좌측 영역 첫 줄)**:
- color: #F74B0B, font-weight: 900
- letter-spacing: cat_letter, text-transform: uppercase
- margin-bottom: 24

**헤드라인 (검정 메인)**:
- font-size: head_size, font-weight: 900
- color: #1A1A1A, letter-spacing: -4
- line-height: 1.02, margin-bottom: 18

**가격 (오렌지 임팩트)**:
- font-size: price_size, font-weight: 900
- color: #F74B0B, letter-spacing: -6
- line-height: 1

**부제 (회색)**:
- font-size: sub_size, font-weight: 700
- color: #64748B, letter-spacing: -0.3
- margin-top: 28, line-height: 1.45

### 4.5 본문 카드 (2~5) 공통 CSS (body_card_css)

**1x1**: pad_top 100, pad_bot 320, h2_size 58, body_size 30, bar_w 9, bar_pad 30
**4x5**: pad_top 130, pad_bot 400, h2_size 69, body_size 37, bar_w 11, bar_pad 34
**9x16**: pad_top 160, pad_bot 600, h2_size 84, body_size 44, bar_w 14, bar_pad 40

**레이아웃 구조 (★ 수직 중앙 정렬)**:
```
.card (1080 × h)
  └ .content (height: 100%, flex column, padding=pad_top/pad_bot)
      ├ h2 (상단 고정, flex-shrink: 0, margin-bottom: 50px)
      └ .body-zone (flex: 1, justify-content: center)
          └ 본문 + 추가 박스/특수 요소  ← 영역 안에서 수직 중앙 정렬
```
- `.content`: height 100% + display flex + flex-direction column
- `.body-zone`: flex 1 + display flex + flex-direction column + justify-content center
- card_wrap이 content_html을 `</h2>` 기준으로 자동 분리 → h2는 상단 고정, 나머지는 .body-zone으로 감쌈
- 카드 2~6 모두 동일 적용 (카드 6은 include_logo=False)

**h2 (헤드라인)**:
- border-left: bar_w solid #F74B0B (좌측 오렌지 막대)
- padding-left: bar_pad
- font-weight: 900, line-height: 1.18, letter-spacing: -2.5
- margin-bottom: 50, flex-shrink: 0

**body-text**:
- font-weight: 600, line-height: 1.65, letter-spacing: -0.5
- color: #1A1A1A
- `.body-text b` → font-weight 900
- `.body-text .hl` → color #F74B0B, font-weight 900

**source (출처)**:
- font-size: body_size * 0.78
- color: #94A3B8, font-weight: 600

**page-ind (페이지 번호)**:
- 1x1: bottom 70, right 60, font-size 24
- 4x5: bottom 80, right 80, font-size 26
- 9x16: bottom 100, right 80, font-size 32

### 4.6 카드 2~5 추가 디자인 요소

**Card 3 (큰 숫자 임팩트)**:
- big_num: 1x1=160, 4x5=200, 9x16=200
- color: #F74B0B, font-weight: 900, letter-spacing: -8
- white-space: nowrap (한 줄 보장)

**Card 4 (★ 자유 디자인 - 카드 5와 동일 원칙)**:
- 디자인 원칙: 카드 4도 매 기사마다 콘텐츠에 맞는 UI를 새로 짠다. STEP 박스 3개는 단지 한 옵션.
- 콘텐츠 성격에 따라: 비교 표, 큰 숫자, 인용 박스, 그래프 등 자유롭게
- **현재 사례 (STEP 박스 3개)** — galaxy_zfold8_lineup, family_month_telcom_2026 등에서 사용:
  - 1x1: spec_size 35, label_size 23, pad "22px 30px", mb 14
  - 4x5: spec_size 44, label_size 28, pad "30px 38px", mb 20
  - 9x16: spec_size 46, label_size 30, pad "30px 40px", mb 20
  - 박스 배경: #F8FAFC, 좌측 border 6px solid #F74B0B
  - label: color #94A3B8, font-weight 800
  - value: color #1A1A1A, font-weight 900

**Card 5 (★ 자유 디자인 - 고정 템플릿 금지)**:
- 디자인 원칙: 카드 5는 매 기사마다 콘텐츠에 맞는 UI를 새로 짠다. 검정 박스, STEP 박스 같은 고정 템플릿 사용 금지.
- 콘텐츠 성격에 따라 자유롭게: 5행 리스트, 비교 표, 큰 숫자, 그래프, 인용 박스 등
- 다른 카드(2~4)와 시각적으로 구별되는 형식을 골라야 카드뉴스 전체 리듬이 살아남
- **현재 family_month_telcom_2026 사례 — 5행 리스트형**:
  - 1x1: age_size 26, brand_size 30, row_pad 18, mt 30
  - 4x5: age_size 32, brand_size 36, row_pad 22, mt 50
  - 9x16: age_size 40, brand_size 44, row_pad 26, mt 60
  - 행 구조: `display: flex; justify-content: space-between; align-items: baseline; padding: row_pad 0; border-bottom: 2px solid #E2E8F0`
  - 좌측 라벨: 오렌지 #F74B0B, font-weight 900
  - 우측 값: 검정 #1A1A1A, font-weight 800
  - 마지막 행만 border-bottom 제거
- **과거 사례 (참고용)**: 검정 인포 박스 (#1A1A1A 배경 + 흰 글씨) — galaxy_zfold8_lineup, voice_phishing_care, face_auth_july 등에서 사용. 이제 "기본"이 아니라 콘텐츠가 어울릴 때만 선택지로.

### 4.7 카드 6 (CTA - 큰 로고 가운데)

**구조**: h2 + 본문 (가운데 정렬, 2줄) + 큰 폰스팟 로고 + 안내문
**레이아웃**: card_wrap의 body-zone으로 자동 수직 중앙 정렬 (4.5 구조 동일 적용)

**1x1**: big_logo_h 95, body_size 36, sub_size 22, body_mt 30, logo_mt 30
**4x5**: big_logo_h 119, body_size 44, sub_size 26, body_mt 40, logo_mt 40
**9x16**: big_logo_h 155, body_size 56, sub_size 34, body_mt 60, logo_mt 60

**본문 (2줄, 가운데 정렬)**:
- 첫 줄: 검정 #1A1A1A
- 둘째 줄: 오렌지 #F74B0B
- font-weight 900, letter-spacing -1, line-height 1.4
- 사이 간격: margin-top 8

**로고 이미지**: `logo_color_trimmed.png` (★ trim된 PNG 사용 - 4.8 참조), height: big_logo_h
- 원본 logo_color.png는 161×161에 글자 영역 141×48만 차지 (위/아래 35% 투명 여백)
- trim된 PNG로 교체하면서 height 320/400/520 → 95/119/155로 재계산 (글자 시각 크기 동일)
- 결과: logo_mt 값과 실제 시각 거리가 일치, 위/아래 텍스트와 자연스럽게 가까움

**안내문**: "자세한 내용은 프로필을 확인해주세요"
- font-size: sub_size, font-weight 500
- color: #94A3B8, margin-top: 18
- letter-spacing: -0.3

**중요**: card_wrap 호출 시 include_logo=False (큰 로고 직접 배치, 자동 작은 로고 X)

### 4.8 폰스팟 로고 (3종 PNG)

| 파일 | 크기 | 용도 |
|---|---|---|
| `images/logo_cutout_original.png` | 161×161 (투명 여백 포함) | 카드 2~5 하단 작은 로고 |
| `images/logo_cutout_white.png` | 동일 | 어두운 배경용 (현재 미사용) |
| `images/logo_cutout_trimmed.png` | 141×48 (투명 여백 제거) | ★ 카드 6 큰 로고 전용 |

**카드 2~5 로고 (logo_color.png = original)**:
- 위치: 카드 하단 가운데 (text-align: center)
- 1x1: bottom 50, height 128
- 4x5: bottom 60, height 144
- 9x16: bottom 80, height 176
- 작은 크기에선 투명 여백이 시각적으로 무시 가능 → 원본 그대로 사용

**카드 1**: 로고 없음 (매거진 표지)
**카드 6**: trim된 큰 로고 가운데 (95/119/155px - 4.7 참조)

**trim 생성 방법** (logo_cutout_original.png 변경 시 재생성 필요):
```python
from PIL import Image
img = Image.open('images/logo_cutout_original.png')
img.crop(img.getbbox()).save('images/logo_cutout_trimmed.png')
```

**renderer 상단 (3 사이즈 폴더 자동 복사)**:
```python
LOGO_TRIM_SRC = BASE / 'images' / 'logo_cutout_trimmed.png'
# for sz 루프 안:
if LOGO_TRIM_SRC.exists():
    shutil.copy(LOGO_TRIM_SRC, OUT / sz / 'logo_color_trimmed.png')
```

---

## 5. 워크플로우 (새 기사 작업)

### Step 1: 기사 선별 (Claude 자동)
- WebSearch + Chrome MCP로 etnews 통신 섹션 직접 fetch
- 발행일 검증 (URL 패턴 + 본문 발행일 confirm)
- 폰스팟 매칭도 평가 (3 후보 추천)

### Step 2: 슬러그 결정
- 영문 snake_case (예: `voice_phishing_care`, `face_auth_july`)
- `articles/<slug>.json` 빈 파일이라도 생성 → run_windows.py가 SLUG 자동 인식

### Step 3: 카드 1 이미지 생성
- 종민님이 ChatGPT 또는 nano-banana로 직접 생성
- 저장: `images/<slug>/cover.png`
- 1080x1080 1:1 비율

#### ★ 표준 베이스 프롬프트 (최종 v2 — 매거진 레이아웃 호환)
카드 1은 매거진 스타일(cover 풀스크린 + **좌측 fade gradient + 좌측 텍스트 오버레이**). 따라서 **폰은 우측에 / 좌측 50%는 빈 배경**이어야 텍스트 가독성 확보. SUBJECT는 3요소 (메인+컨텍스트+무드) 명시 필수. ChatGPT 동화책 일러스트·과한 광고 톤 모두 차단.

```
Premium editorial cover photography for a tech magazine — single subject focus.

SUBJECT (★ 3요소 필수):
1. MAIN OBJECT: [폰 1대 / 카드 / 단말기 등 — 단일 메인 객체], shown at a 
   slight 25-degree angle, slightly tilted upright.
2. CONTEXT SIGNAL: [주제와 직결되는 시각 단서 1개 — 실물 사진 형태]
   예 - 한정 행사: small white gift box with thin satin ribbon, partially 
        visible behind the phone (real photography, NOT illustrated)
   예 - 신제품 출시: small acrylic display stand or subtle countdown marker
   예 - 보안/차단: phone screen showing minimalist call-block UI (no text)
   예 - 가격/혜택: subtle gold price tag silhouette behind the phone
   ★ 추가 객체 반드시 실물 사진 형태, 일러스트/아이콘/이모지 금지
3. MOOD COLOR: [폰 화면 글로우 컬러를 주제 무드에 맞춤]
   예 - 한정 행사·시즌: warm coral-to-gold (anticipation/celebration)
   예 - 보안·경고: cool blue-to-cyan (alert)
   예 - 시니어/부모님: warm peach-to-cream (caring)
   예 - 신제품 출시: deep navy-to-violet (premium reveal)

★ COMPOSITION (★ 카드 1 매거진 레이아웃 호환 필수):
- Phone positioned on the RIGHT side of frame, occupying ~35-50% of right area
- LEFT 50% must be EMPTY negative space (background only)
- 이는 카드 1의 좌측 fade gradient + 텍스트 오버레이가 폰 위에 겹치지 않게 함
- Context signal은 폰 옆/뒤에 배치, 메인보다 작고 부드러운 포커스

Lighting: SUBTLE soft directional light from upper-right, NOT dramatic sun rays.
Editorial press photo tone, NOT luxury advertisement. Reduce intensity of any 
light beams. Slight reflective surface beneath catching faint warm highlights.

Background: soft [warm cream-beige / cool grey / muted dark] gradient that 
complements the mood color. No patterns.

Style: photorealistic 8K, shot on medium format camera with 85mm macro lens, 
shallow depth of field on main object, magazine cover quality, premium tech 
editorial aesthetic.

STRICT EXCLUSIONS:
- NO multiple main objects (single hero only)
- NO illustrations, NO line art, NO cartoon elements
- NO abstract icons, NO graphic decorations, NO floating shapes
- NO emoji-style hearts/stars/balloons/sparkles
- NO text on screens (UI elements OK if minimal and realistic)
- NO brand logos, NO watermarks
- NO dramatic sun rays / movie poster lighting

Aspect ratio: 1:1 square, 1080x1080.
```

#### 핵심 원칙 (모든 카드뉴스 공통)
- "editorial press photography" / "magazine cover quality" 키워드 필수
- **SUBJECT 3요소** (메인 + 컨텍스트 + 무드) 명시 — 단일 폰 클로즈업만으론 뉴스 컨텍스트 사라짐
- **COMPOSITION 룰** (폰 우측, 좌측 빈 공간) 필수 — 카드 1 매거진 레이아웃과 호환
- "Lighting: subtle, editorial" (NOT dramatic, NOT luxury ad)
- **STRICT EXCLUSIONS 블록 필수** — 일러스트·아이콘·장식·과한 광고 톤 차단

#### v2 변경 이력
- v1 (옵션 A): 단일 폰 클로즈업만 → 뉴스 컨텍스트 사라짐 → ❌
- v2 (현재): SUBJECT 3요소 + 우측 배치 + subtle lighting → ✅ 갤S26 패밀리 페스타에서 검증 완료

### Step 4: 콘텐츠 작성 (★ 누락 주의)
- `scripts/cardnews_renderer_v2.py` 한 파일에 콘텐츠가 **2개 영역**에 분산되어 있음. **두 영역 모두 빠짐없이** 교체해야 함.
- Python 스크립트로 안전하게 (str.replace 패턴, Edit tool은 한글 큰 파일에서 손상 위험)

#### Step 4 체크리스트 (모두 ✅ 되어야 새 기사 완료)

- [ ] **COVER_SRC 경로** (16번 줄 근처): `BASE / 'images' / '<slug>' / 'cover.png'`
- [ ] **카드 1 (60~190줄)** — 5개 텍스트:
  - [ ] `label` (상단 라벨, 예: `NEW · 2026.04.27`)
  - [ ] `category` (영문 카테고리, 예: `FACE AUTH · JULY MANDATE`)
  - [ ] `headline` (메인 헤드라인 1줄)
  - [ ] `price` (서브 헤드라인, 오렌지 컬러)
  - [ ] `subtitle` (회색 서브타이틀)
- [ ] **카드 2 (`render_card_2`)** — h2 / 본문 / 출처
- [ ] **카드 3 (`render_card_3`)** — h2 / 본문 / `big_num` / `big_label`
- [ ] **카드 4 (`render_card_4`)** — h2 / 본문 / 3 STEP 박스 (label + value × 3)
- [ ] **카드 5 (`render_card_5`)** — h2 / 본문 / 검정 인포 박스 (title + body)
- [ ] **카드 6 (`render_card_6`)** — h2 (CTA 본문/로고는 보통 그대로)
- [ ] **CAPTIONS 변수 (430~580줄, ★ 캡션 누락 주의)** — 5채널 모두:
  - [ ] 네이버 블로그 (제목 후보 + 본문 + 매장 안내)
  - [ ] 스레드
  - [ ] 인스타그램 (본문 + 해시태그)
  - [ ] 유튜브 (제목 + 영상 요약 + 타임스탬프 + 핵심 정보 + 매장 안내 + 해시태그)
  - [ ] 틱톡 (본문 + 해시태그)
- [ ] **모듈 docstring** (2번 줄 `"""…카드뉴스 (v4)"""` 첫 줄) — 새 주제로 교체

#### 검증 (작업 직후 1회)

```bash
# 이전 기사 키워드 잔재 검색 — 결과가 0줄이어야 통과
grep -E "이전기사키워드1|이전기사키워드2" scripts/cardnews_renderer_v2.py
```

### Step 5: 자동 실행
- `run_pngs.bat` 더블클릭 → run_windows.py 실행
- run_windows.py가 articles/ 가장 최근 JSON에서 SLUG 자동 인식
- Playwright + Chromium 렌더링 (첫 실행만 130MB 다운로드)
- 18장 JPG (각 ~80KB) + captions.md 생성
- 결과: `output/<slug>/`

### Step 6: 검토 + 발행
- 카드별 read tool로 미리 확인
- 종민님 피드백 → 수정 → 재실행
- SNS 5채널 (네이버 블로그, 스레드, 인스타, 유튜브, 틱톡) 캡션 활용

---

## 6. 코드 핵심 구조

### 6.1 cardnews_renderer_v2.py

```python
# 상단
BASE = Path('/mnt/user-data/outputs/cardnews_tool')  # run_windows.py가 Windows 경로로 치환
OUT = Path('/mnt/user-data/outputs/iphone18_spec_downgrade_v2')  # 동일하게 치환됨

COVER_SRC = BASE / 'images' / '<slug>' / 'cover.png'  # 매번 변경
LOGO_WHITE_SRC = BASE / 'images' / 'logo_cutout_white.png'
LOGO_COLOR_SRC = BASE / 'images' / 'logo_cutout_original.png'

# Logo / Cover 복사 (3개 사이즈 폴더)
for sz in ['1x1', '4x5', '9x16']:
    (OUT / sz).mkdir(exist_ok=True)
    shutil.copy(...)

SIZE_CONFIG = {'1x1': ..., '4x5': ..., '9x16': ...}
FF = '"Pretendard", "Noto Sans KR", "Malgun Gothic", sans-serif'

LOGO_HEIGHT, LOGO_BOTTOM, PAGE_BOTTOM, PAGE_RIGHT, PAGE_SIZE = {...}

GLOBAL_FONT_RESET = '''
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');
* { font-family: ... !important; ... }
'''

def logo_block(size, white=False): ...

def render_card_1(size): ...  # 매거진 표지
def body_card_css(size): ...  # 카드 2~5 공통 CSS
def card_wrap(size, content_html, page_num, include_logo=True): ...  # 카드 2~6 wrapper

def render_card_2(size): ...  # 리드 (h2 + body + source)
def render_card_3(size): ...  # 큰 숫자 임팩트
def render_card_4(size): ...  # 스펙 3개 박스
def render_card_5(size): ...  # 검정 정보 박스
def render_card_6(size): ...  # 큰 로고 가운데 (include_logo=False)

# 메인 렌더 루프 (Playwright)
HAS_COVER = COVER_SRC.exists()
RENDERERS = [...] (cover 있으면 6개, 없으면 5개)

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    for size, cfg in SIZE_CONFIG.items():
        ctx = browser.new_context(viewport={'width': cfg['w'], 'height': cfg['h']})
        page = ctx.new_page()
        for i, render_fn in RENDERERS:
            html = render_fn(size)
            html_path.write_text(html, encoding='utf-8')
            page.goto('file:///' + html_path.as_posix())
            page.wait_for_load_state('networkidle', timeout=8000)
            page.screenshot(path=jpg_path, type='jpeg', quality=85, ...)
    browser.close()

# Cleanup (logo, cover.png 삭제)
# captions.md 생성 (5채널)
```

### 6.2 run_windows.py

```python
SLUG = os.environ.get('SLUG') or articles/ 가장 최근 JSON stem
OUT = BASE / 'output' / SLUG

# cardnews_renderer_v2.py 코드 읽고 sandbox 경로 → Windows 경로 치환
src = src.replace("Path('/mnt/.../cardnews_tool')", f"Path(r'{BASE}')")
src = src.replace("Path('/mnt/.../iphone18_spec_downgrade_v2')", f"Path(r'{OUT}')")

# wkhtmltoimage 자동 탐색 (백업, 현재는 사용 안 함)
# Playwright + Chromium 자동 설치
exec(compile(src, ...))
```

### 6.3 run_pngs.bat

```bat
@echo off
cd /d C:\Users\di898\Documents\phonespot_cardnews
set PYTHONIOENCODING=utf-8

py -3 scripts\run_windows.py >> run_log.txt 2>&1
```

---

## 7. 트러블슈팅 (이전 겪은 문제 + 해결)

### 7.1 폰트 적용 안 됨 (Pretendard → 굴림체 fallback)
- **원인**: wkhtmltoimage가 OTF 시스템 폰트 못 찾음, weight 900 매칭 실패
- **해결**: Playwright + Chromium 사용 (CDN @import 잘 인식)
- **현재**: 정상 작동

### 7.2 카드 1 흰 텍스트 가독성 (이미지 위)
- **원인**: 이미지가 흰 배경이라 흰 글씨 묻힘
- **해결**: 매거진 스타일 — 검정 헤드라인 + 좌측 흰 페이드로 텍스트 영역 가독성 보장
- **9x16 별도 처리**: 이미지를 카드 가운데 정렬, 위/아래 빈 영역에 텍스트

### 7.3 PNG 사이즈 4MB
- **해결**: Playwright `screenshot(type='jpeg', quality=85)` 직접 출력
- **결과**: 4MB → 80KB (50배 절감)

### 7.4 Edit tool로 큰 한글 파일 수정 시 손상
- **현상**: 파일 끝이 잘림, null bytes 삽입
- **해결**: Python 스크립트로 직접 수정 (str.replace + open write)
- **Code**: `python3 << 'PYEOF' ... PYEOF` heredoc 사용

### 7.5 Sandbox stat 캐시
- **현상**: 파일 mtime이 갱신 안 보임 (sandbox)
- **확인**: md5sum 또는 직접 read tool로 검증
- **실제 Windows 파일 시스템에서는 정상 갱신됨**

### 7.6 Chromium 처음 실행 시간
- **첫 실행**: Playwright + Chromium 130MB 다운로드 (5~10분)
- **두 번째부터**: 약 10~15초 (정상)

---

## 8. 백업 정책

**자동 백업 파일 (보존)**:
- `cardnews_renderer_v2_backup_iphone18.py` (가장 처음 버전, SVG 기반)
- `cardnews_renderer_v2_backup_moto_g77.py` (모토 g77 작업 시점)
- `cardnews_renderer_v2_backup_inline.py` (voice_phishing_care inline)
- `cardnews_renderer_v2_backup_wkhtml.py` (wkhtmltoimage + JPG 직접 출력)

**작업 전 권장**: 새 기사 작업 시작 전에 현재 cardnews_renderer_v2.py를 backup_<날짜>.py로 복사

---

## 9. 미래 개선 옵션 (적용 가능)

### 9.1 콘텐츠 JSON 완전 분리 (★★★)
- 현재: 매번 cardnews_renderer_v2.py 직접 수정
- 개선: `articles/<slug>.json`에 카드 1~6 모든 데이터 + captions
- 렌더러는 JSON만 읽어 렌더링 → 매번 JSON만 새로 작성
- 이미 articles/voice_phishing_care.json, face_auth_july.json 더미 있음

### 9.2 사이즈별 병렬 렌더링 (★★)
- 현재: 1x1 → 4x5 → 9x16 순차
- 개선: ProcessPoolExecutor로 3개 동시
- 예상: 30~40초 → 10~15초

### 9.3 SNS 자동 업로드 (★★★★)
- 네이버 블로그 BLOG2 API → 제목 + 본문 + 카드뉴스 18장 자동 게시
- 인스타 Graph API → Carousel (비즈니스 계정 + Facebook 페이지 연동 필요)
- 스레드 Threads API → 단문 + 이미지
- 유튜브/틱톡: 카드뉴스 → 영상 변환 (ffmpeg) → 자동 업로드

### 9.4 매일 아침 RSS 자동 추천 (★★★)
- Cowork scheduled task로 매일 8시 etnews/ZDNet/디지털데일리 fetch
- 신선 기사 3개 자동 선별 → 푸시 알림으로 종민님께
- 1개 선택 → 자동 카드뉴스 작업 시작

### 9.5 카드 1 이미지 자동 생성 (★★)
- 현재: ChatGPT 직접 생성 (수작업)
- 개선: Gemini API (`scripts/generate_image.py` 이미 작성됨, gemini_key.txt만 등록 필요)
- 비용: Imagen 4 Fast ~월 1,650원 (월 60장 기준)

---

## 10. 폰스팟 핵심 규칙 (PROJECT_INSTRUCTIONS 발췌)

**브랜드**:
- 폰스팟 광교점만 (안양점은 운영 중단, 모든 컨텐츠에서 안양 언급 금지)
- KT 공식 인증 대리점
- 시세비교: citymarket.co.kr/pb
- SNS 허브: litt.ly/phonespot

**캡션 필수**:
- 모든 캡션 하단에 사전승낙서 URL: `https://ictmarket.or.kr:8443/precon/pop_CertIcon.do?PRECON_REQ_ID=PRE0000194479&YN=1`

**카드 디자인 필수**:
- 로고 하단 중앙 (카드 2~5)
- 카드 이미지에 litt.ly URL 표기 X (캡션에만)
- "넘겨보기" / "위로 스와이프" 안내 문구 X
- 고정 슬로건 사용 금지, 기사별 브리지 CTA

---

## 11. 유지보수 체크리스트

매월 1회 점검:
- [ ] Pretendard CDN 주소 유효 (jsdelivr 정책 변경 가능)
- [ ] 사전승낙서 URL 갱신 여부
- [ ] etnews/zdnet 등 매체 URL 패턴 변경
- [ ] Chromium 버전 업데이트 (`playwright install chromium --force`)
- [ ] 이전 기사 output/ 폴더 백업 (Dropbox 등) + 정리

---

## 12. 비상 복구 시나리오

**케이스 1**: cardnews_renderer_v2.py 손상
- backup 파일 중 가장 최근 (cardnews_renderer_v2_backup_inline.py 또는 _wkhtml.py)에서 복원
- Python 스크립트로 콘텐츠 + COVER_SRC 다시 변경

**케이스 2**: Chromium 다운로드 실패
- 인터넷 연결 확인
- 명령: `py -3 -m playwright install chromium --force`
- 안 되면 wkhtmltoimage 백업 모드로 전환 (cardnews_renderer_v2_backup_wkhtml.py 사용)

**케이스 3**: 폰트 깨짐
- CDN 접속 확인
- @import URL이 정확한지 (gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css)
- Windows 시스템에 Pretendard OTF 9종 설치 (백업)

**케이스 4**: 한글 깨짐 (cmd에서 ?? 표시)
- run_pngs.bat에 `set PYTHONIOENCODING=utf-8` 있는지 확인
- chcp 65001 명령 추가

---

## 끝

이 문서를 기반으로 누구든 phonespot_cardnews 자동화 시스템을 100% 복원할 수 있다.
디테일이 부족한 부분은 cardnews_renderer_v2.py 코드를 직접 참고할 것.

마지막 업데이트: 2026-04-28
