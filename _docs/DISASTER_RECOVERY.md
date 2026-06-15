# 재해 복구 (Disaster Recovery) — 2026-06-11 신설

> **상태: Phase 1 셋업 완료 시점 기준.** PC 손상·실수 삭제·교체 시 복구 절차.
> 클라우드 (Google Sheets / Apps Script / Drive) 데이터는 PC와 무관하게 자동 보호.

---

## 한 줄 요약

GitHub repo (`313jongmin-droid/phonespot-cardnews-video`) + Google 클라우드 + Drive 데스크톱 sync = 3중 백업. 로컬 PC 망가져도 코드/데이터 거의 100% 복구. 단 `_secrets/`는 별도 백업 필수.

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
| `_secrets/` (API 키 / 토큰) | ⚠️ **로컬 PC만** | ⚠️ **별도 백업 필수** |
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

# 4. _secrets/ 별도 백업에서 복원 (있으면)
copy <백업위치>\_secrets phonespot_cardnews\_secrets

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

### 6. _secrets/ 별도 백업에서 복원
- 1Password / Bitwarden / 외장 HDD 등에서 복원

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

## ⚠️ _secrets/ 별도 백업 절차 (필수)

`_secrets/`는 git에 안 들어감 (보안). PC 망가지면 사라짐. **별도 백업 필수.**

### 박힌 비밀
- `_secrets/meta_token.txt` (메타 시스템 사용자 토큰)
- `_secrets/naver_api_license.txt` / `naver_secret_key.txt` (네이버 검색광고)
- `_secrets/gemini_key.txt` (Gemini API)
- `_secrets/telegram_token.txt` / `telegram_chat_id.txt` (텔레그램 listener)
- 기타 채널별 API 키

### 권장 백업 방법
1. **1Password / Bitwarden** — 비밀번호 관리자에 텍스트로 저장 (가장 안전)
2. **외장 HDD / USB** — `_secrets/` 폴더 통째 복사 (분기/연 1회)
3. **개인 Drive** — 암호화한 zip으로 업로드 (단 Drive 손상 위험 고려)

### Apps Script PropertiesService에 있는 것 (재발급 절차)
- `META_TOKEN` / `META_AD_ACCOUNT_ID` — Meta Business Manager에서 재발급
- `INSTAGRAM_BUSINESS_ID` — 메타 페이지 설정에서 확인 (`17841474706647015`)
- `NAVER_API_LICENSE` / `NAVER_SECRET_KEY` / `NAVER_CUSTOMER_ID` — ads.naver.com → API 사용 관리
- `APIFY_TOKEN` — apify.com 계정 설정
- `GEMINI_API_KEY` — Google AI Studio

→ **Apps Script PropertiesService 자체는 Google 클라우드라 PC와 무관.** 콘솔에서 그대로 보임.

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
- **`_secrets/` 백업 안 했는데 PC 망가짐** — 모든 API 키 재발급 필요

### 권장 사전 대비
1. GitHub + Google 계정 모두 **2FA 활성화**
2. `_secrets/` **월 1회 백업** (1Password 또는 외장 HDD)
3. 분기별 **복구 절차 한 번 시뮬레이션** (다른 폴더에 clone해서 동작 확인)

---

작성: 2026-06-11
