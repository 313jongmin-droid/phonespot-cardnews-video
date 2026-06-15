# 재해 복구 (Disaster Recovery) — 2026-06-11 신설

> **상태: Phase 1 셋업 완료 시점 기준.** PC 손상·실수 삭제·교체 시 복구 절차.
> 클라우드 (Google Sheets / Apps Script / Drive) 데이터는 PC와 무관하게 자동 보호.

---

## 한 줄 요약

GitHub repo (`313jongmin-droid/phonespot-cardnews-video`) + Google 클라우드 + Drive 데스크톱 sync = 3중 백업. 로컬 PC 망가져도 코드/데이터 거의 100% 복구. `_secrets/`는 백업 안 함 (사장님 결정 2026-06-15) — 손실 시 재발급 절차(아래 섹션)로 45분~1h.

---

## 무엇이 어디 있나 (백업 출처 매트릭스)

| 자산 | 저장 위치 | PC 손상 영향 |
|---|---|---|
| **공용 코드** (Code.gs, meta-sync.gs, naver-sync.gs, youtube_sync.gs, generator.html) | GitHub repo + Apps Script 콘솔 (이중) | 영향 0 |
| **카드뉴스 코드** (cardnews/scripts, webui, templates) | GitHub repo | 영향 0 |
| **영상 코드** (shorts/promo, shorts/promo_ai) | GitHub repo | 영향 0 |
| **자동화 코드** (automation/scripts) | GitHub repo | 영향 0 |
| **가이드** (CLAUDE.md, _docs/, ads/) | GitHub repo | 영향 0 |
| **카드뉴스 기사 JSON** (cardnews/articles/) | GitHub repo (git 추적) | 영향 0 |
| **GitHub Actions workflow** (.github/workflows/) | GitHub repo | 영향 0 |
| **Google Sheets 데이터** (광고운영 관리대장 등) | Google 클라우드 | 영향 0 |
| **Apps Script 콘솔 코드** | Google 클라우드 | 영향 0 |
| **Drive 일러스트 허브** (PhoneSpot_Library) | Drive 클라우드 + 데스크톱 sync | 영향 0 (데스크톱 sync만 재설정) |
| `_secrets/` (API 키 / 토큰) | 로컬 PC만 (사장님 결정: 백업 X) | 손실 시 재발급(45분~1h). 광고운영 Apps Script는 PropertiesService 사용이라 무영향 |
| `.clasprc.json` (clasp OAuth 토큰) | 로컬 `C:\Users\<user>\.clasprc.json` | `clasp login` 재실행으로 복구 |
| `apps_script/.clasp.json` (Script ID) | 로컬 + GitHub Secrets `CLASP_JSON` | Apps Script 콘솔에서 다시 확인 가능 |
| `node_modules/` | 로컬만 | `npm install`로 재생성 |
| `cardnews/images/`, `shorts/out/` (1GB+) | 로컬 + Drive (이미지만) | 카드 이미지는 Drive sync, 영상 출력은 재렌더 |
| 임베딩 DB (`shorts/config/illustration_tag_db.json` 등) | 로컬만 | SETUP_FULL_PRODUCER.bat으로 재구축 |

---

## 시나리오 A — 로컬 폴더 일부 손상 / 실수 삭제 (가장 흔함)

**소요: 5분**

```bash
# 1. 손상된 폴더 백업 (혹시 모를 자산 보존)
ren phonespot_cardnews phonespot_cardnews_broken

# 2. 새로 clone
cd C:\Users\<user>\Documents
git clone https://github.com/313jongmin-droid/phonespot-cardnews-video.git phonespot_cardnews

# 3. Apps Script 코드 동기화
cd phonespot_cardnews\apps_script
clasp pull             # Apps Script 콘솔 최신 코드 다운로드

# 4. _secrets/ 재발급 (백업 안 함, 사장님 결정 2026-06-15)
# → 아래 "_secrets/ 손실 시 재발급 절차" 섹션 참고. 45분~1h.

# 5. 일러스트 Drive sync 확인 (PhoneSpot_Library 데스크톱 sync 활성 상태)

# 6. 검증 (아래 "복구 검증" 참고)
```

---

## 시나리오 B — PC 교체 / 새 PC Bootstrap

**소요: 30분~1시간**

### 1. 사전 설치 (15분)
- **Node.js LTS** — nodejs.org → Windows Installer
- **Git for Windows** — git-scm.com → 64-bit Standalone Installer
- 둘 다 기본값 그대로 Next. **단 Git 설치 시 "Git from the command line and also from 3rd-party software"** 선택
- 설치 후 명령 프롬프트 재시작

### 2. clasp 설치 + 로그인 (5분)
```cmd
npm install -g @google/clasp@3.3.0
clasp login            # 브라우저 OAuth → 313jongmin@gmail.com 선택 → 권한 승인
```

### 3. Git 설정 (2분)
```cmd
git config --global user.name "313jongmin"
git config --global user.email "313jongmin@gmail.com"
```

### 4. GitHub repo clone (3분)
```cmd
cd C:\Users\<user>\Documents
git clone https://github.com/313jongmin-droid/phonespot-cardnews-video.git phonespot_cardnews
cd phonespot_cardnews
```

### 5. Apps Script 코드 동기화 (1분)
```cmd
cd apps_script
clasp pull
cd ..
```

### 6. _secrets/ 재발급 (백업 안 함, 사장님 결정 2026-06-15)
- 아래 "_secrets/ 손실 시 재발급 절차" 섹션의 키별 발급 URL + 절차대로. 45분~1h.
- **광고운영 Apps Script 자동화는 PropertiesService 사용이라 무영향** = 6번 step 생략 가능 (로컬 텔레그램 listener 사용 안 하면).

### 7. (카드뉴스/영상 사용 시) 풀 셋업
```cmd
CODEX_VIDEO_DESK\SETUP_FULL_PRODUCER.bat
```

### 8. (Drive 일러스트 사용 시) 데스크톱 sync 셋업
- Google Drive 데스크톱 앱 설치
- `PhoneSpot_Library` 폴더 sync 활성화
- `shorts/config/library_share_path.txt`에 로컬 경로 박기

### 9. 검증 (아래)

---

## 시나리오 C — GitHub repo 자체 삭제 (극단)

**대응:**
1. **다른 PC에 clone 본이 있으면** → 거기서 새 repo 만들고 force push (30분)
2. **GitHub Support 복구 요청** — github.com/contact → repo 삭제 30일 이내면 복구 가능
3. **모든 백업 잃은 경우** — Apps Script 콘솔에서 `clasp clone <Script-ID>` + 로컬에 남은 가이드 백업으로 부분 복원

---

## _secrets/ 손실 시 재발급 절차 (사장님 결정 2026-06-15: 백업 안 함 / 재발급으로 처리)

`_secrets/`는 git에 안 들어감 (보안 룰, `.gitignore` 3회 박힘). **사장님 결정 = 별도 백업 안 함**. PC 손상 시 = 재발급(45분~1시간). HDD 손상 확률 낮음 + 재발급 시간 감수 가능 = 합리적 결정.

### 저장 위치 (어디서 사용되나)
| 키 | 저장 위치 | 사용처 |
|---|---|---|
| `META_TOKEN` / `META_AD_ACCOUNT_ID` / `INSTAGRAM_BUSINESS_ID` | **Apps Script PropertiesService** (Google 클라우드) | 메타·인스타 자동화 (Apps Script) — **PC 손상 무관** |
| `NAVER_API_LICENSE` / `NAVER_SECRET_KEY` / `NAVER_CUSTOMER_ID` | **Apps Script PropertiesService** | 네이버 검색광고 자동화 — **PC 손상 무관** |
| `GEMINI_API_KEY` | **Apps Script PropertiesService** | 메타·유튜브 인사이트 분석 — **PC 손상 무관** |
| `APIFY_TOKEN` | **Apps Script PropertiesService** | Apify Meta Ad Library 벤치마크 — **PC 손상 무관** |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | **로컬 `_secrets/telegram_token.txt` + GitHub Secrets** | 카드뉴스 텔레그램 listener (로컬) + Actions 실패 알림 (GitHub) — **PC 손상 시 로컬만 영향, GitHub은 무관** |
| `CLASPRC_JSON` / `CLASP_JSON` | **GitHub Secrets** (GitHub 클라우드) | Apps Script 자동 배포 — **PC 손상 무관** |

→ **결론**: `_secrets/` 폴더 사라져도 **광고운영 자동화(Apps Script)는 무영향**. 영향 받는 건 **로컬 텔레그램 listener** 정도 — 텔레그램 봇 토큰 재발급 또는 GitHub Secrets에서 복사.

### 재발급 절차 (각 키별)

**1. META_TOKEN (메타 시스템 사용자 토큰)**
- URL: https://business.facebook.com → 비즈니스 설정 → 시스템 사용자 (`phonespot-sync`)
- 절차: 시스템 사용자 선택 → "새 토큰 생성" → 권한 선택 (`ads_read`, `ads_management`, `business_management`, `pages_read_engagement`, `instagram_basic`, `instagram_manage_insights`) → 토큰 복사
- **★ 인스타 시스템 사용자 자산 추가는 토큰 발급 전에 미리** (발급 후 자산 추가하면 scopes 반영 안 됨 — 2026-06-11 학습 사실)
- 등록: Apps Script 콘솔 → 프로젝트 설정 → 스크립트 속성 → `META_TOKEN` 값 갱신
- 검증: 시트 메뉴 🛠 폰스팟 운영 → 🔑 토큰 연결 테스트 → ✅

**2. NAVER_API_LICENSE / NAVER_SECRET_KEY (네이버 검색광고)**
- URL: https://manage.searchad.naver.com → 도구 → API 사용 관리
- 절차: 새 API 키 생성 (License Key + Secret Key 동시 발급)
- 등록: Apps Script 콘솔 → 스크립트 속성 → `NAVER_API_LICENSE`, `NAVER_SECRET_KEY` 값 갱신
- 검증: 시트 메뉴 🔍 네이버 자동화 → 🔑 연결 테스트 → ✅

**3. GEMINI_API_KEY**
- URL: https://aistudio.google.com/apikey
- 절차: "Create API key" → Google Cloud 프로젝트 선택 → 키 생성 (즉시 발급)
- 등록: Apps Script 콘솔 → 스크립트 속성 → `GEMINI_API_KEY` 값 갱신
- 검증: 시트 메뉴에서 인사이트 MD 생성 함수 수동 실행 (`generateMetaInsightsMarkdown`)

**4. APIFY_TOKEN**
- URL: https://console.apify.com/account/integrations
- 절차: "API tokens" → "Create new token" → 권한 선택 → 토큰 복사
- 등록: Apps Script 콘솔 → 스크립트 속성 → `APIFY_TOKEN` 값 갱신
- 검증: generator.html → 🎯 벤치마크 탭 → 수집 테스트 → ✅

**5. TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID**
- URL: https://t.me/BotFather (텔레그램 앱 또는 웹)
- 절차: `/mybots` → 봇 선택 → "API Token" → 토큰 복사. 또는 새 봇 만들기 `/newbot`
- chat_id 확인: 봇과 대화 시작 → `https://api.telegram.org/bot<TOKEN>/getUpdates` → `chat.id` 확인
- 등록 (2곳):
  - 로컬: `_secrets/telegram_token.txt` + `_secrets/telegram_chat_id.txt` 파일 새로 만들기
  - GitHub Secrets: https://github.com/313jongmin-droid/phonespot-cardnews-video/settings/secrets/actions → `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 갱신
- 검증: workflow 일부러 실패시켜서 알림 도착 확인 (또는 로컬 `automation/scripts/tg_send.py` 테스트)

### 정직한 한계
- `INSTAGRAM_BUSINESS_ID` = 메타 페이지 자산 ID (`17841474706647015`). 변하지 않는 값 = **이 가이드 자체에 박혀있어서 재발급 불필요**. 메타 페이지 → 설정 → 비즈니스 통합에서도 다시 확인 가능.
- `META_AD_ACCOUNT_ID` = 광고 계정 ID. 메타 비즈매니저에서 확인 (변하지 않음, 한 번 등록하면 영구).
- 키마다 **재발급 시 옛 키 무효화** = 다른 자동화에서 같은 키 쓰면 동시에 갱신 필요.

---

## ⚠️ GitHub Secrets 백업 (CLASPRC_JSON / CLASP_JSON)

GitHub Secrets는 GitHub 클라우드에 있어서 PC 손상과 무관. 단:
- **GitHub 계정 자체 잃으면** 복구 불가 → 2FA + 백업 코드 필수
- 새 PC에서 `clasp login` 재실행 시 새 OAuth 토큰 생성 → 그 토큰을 다시 GitHub Secret에 등록 가능

---

## 복구 검증 절차

복구 후 정상 동작 확인:

### 1. git 상태 확인
```cmd
cd phonespot_cardnews
git status                    # "nothing to commit, working tree clean" 또는 의도된 변경만
git log --oneline -5          # 최근 5개 커밋 정상
```

### 2. clasp 연결 확인
```cmd
cd apps_script
clasp status                  # Logged in. Script ID 표시
clasp pull                    # 에러 없이 실행 (콘솔에서 가장 최근 변경 못 받은 게 있으면 갱신)
```

### 3. Apps Script 콘솔 동작 확인
- 시트 메뉴 **🛠 폰스팟 운영 → 🔑 토큰 연결 테스트** (메타)
- **🔍 네이버 자동화 → 🔑 연결 테스트**
- 모두 ✅ 성공 메시지

### 4. GitHub Actions 워크플로우 확인
- github.com/313jongmin-droid/phonespot-cardnews-video/actions
- 가장 최근 workflow run 초록 ✅

### 5. (카드뉴스/영상 사용 시) 패널 환경 점검
- 패널 "관리 → 환경 점검" PASS

---

## 멀티 브랜드 신설 시 동일 절차 활용 (Bonus)

KT/국민/진짜폰스팟 추가할 때도 같은 Bootstrap 활용:
1. 새 스프레드시트 + Apps Script 생성
2. 새 Script ID 확보
3. **시나리오 B의 4-5번**과 동일 절차 (clone + clasp clone)
4. brand 폴더로 분리 (`brands/kt/`, `brands/kookmin/` 등)
5. GitHub Secret `CLASP_JSON_KT` 추가
6. workflow에 step 1개 추가

→ MULTI_BRAND_ARCHITECTURE.md "Phase 1 셋업 완료" 섹션 참고.

---

## 정직한 한계

### 복구 못 하는 것 (사전 방지가 유일)
- **GitHub 계정 자체 잃음** — 2FA + 백업 코드로 사전 방지
- **Google 계정 잃음** (313jongmin@gmail.com) — 2FA + 복구 이메일 사전 등록

### `_secrets/` (사장님 결정 2026-06-15: 백업 안 함)
- 손실 시 = 위 "재발급 절차"대로 45분~1h 작업.
- **광고운영 자동화 (Apps Script PropertiesService)는 무영향** — `_secrets/` 사라져도 메타·네이버·인스타·GA4 동기화 계속 작동.
- 영향 받는 건 로컬 텔레그램 listener 정도 — 텔레그램 토큰만 재발급하면 복구.

### 권장 사전 대비
1. GitHub + Google 계정 모두 **2FA 활성화**
2. 분기별 **복구 절차 한 번 시뮬레이션** (다른 폴더에 clone해서 동작 확인)

---

작성: 2026-06-11 / 2026-06-15 _secrets 섹션 갱신 (백업 X 결정 + 재발급 절차)
