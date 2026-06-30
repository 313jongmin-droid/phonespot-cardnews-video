# 멀티 브랜드 모노레포 아키텍처 (2026-06-11)

> **상태: Phase 1 셋업 완료 (2026-06-11 16:00 KST). 멀티 브랜드 활성화 = 다른 task `generator.html` 작업 종료 후 KT/국민/진짜폰스팟 신설 시점.**
> 폰스팟 본점 외에 KT다이렉트샵·국민인터넷·진짜 폰스팟(판매점 가입형) 등 브랜드 확장 예정.
> 공용 업데이트(코드 1곳 → N브랜드 반영) + 브랜드 전체 통합(광고/카드뉴스/영상 모듈 한 폴더).

---

## ✅ Phase 1 셋업 완료 (2026-06-11)

### 구성
- **로컬**: `apps_script/` 폴더 (clasp clone 9파일: Code.js, meta-sync.js, naver-synce.js, youtube_sync.js, generator.html, index.html, style.html, test.js, appsscript.json)
- **GitHub repo**: `313jongmin-droid/phonespot-cardnews-video` (단일 진실 원천)
- **인증**: `313jongmin@gmail.com` OAuth (clasp 3.3.0 + scopes: script/drive/userinfo)
- **자동 배포**: `.github/workflows/deploy-apps-script.yml` (Node 20 + clasp 3.3.0 + clasp push --force)
- **GitHub Secrets**:
  - `CLASPRC_JSON` — `C:\Users\<user>\.clasprc.json` 통째 (multiline OK)
  - `CLASP_JSON` — `apps_script/.clasp.json` (★ **반드시 한 줄 압축 JSON**)
- **보안**: `.gitignore`에 `apps_script/.clasp.json`+`apps_script/.clasprc.json` 박힘
- **Git for Windows 2.54.0** 설치 (PowerShell/cmd에서 git 명령 사용 가능)

### 동작 (자동 배포 흐름)
```
사용자 → Apps Script 콘솔 수정 (또는 로컬 수정)
   ↓
cd apps_script && clasp pull          (로컬 동기화, 콘솔 수정 시)
   ↓
cd .. && git add apps_script && git commit && git push origin main
   ↓
GitHub Actions 자동 트리거 (paths: apps_script/** OR workflow_dispatch)
   ↓
Node 설치 → clasp 설치 → CLASPRC_JSON 복원 → CLASP_JSON 복원 → clasp push --force
   ↓
폰스팟 본점 Apps Script 콘솔에 자동 배포 ✅
   ↓ (멀티 브랜드 신설 시, 같은 workflow에 step 추가)
KT/국민/진짜폰스팟 Apps Script도 자동 배포
```

### ⚠️ 함정 (실제 사고 사례)
1. **CLASP_JSON Secret은 한 줄 압축 JSON이어야 함.**
   - 12줄 multiline JSON (메모장 그대로 복사) → `JSON5: invalid character 'P' at 12:1` 에러로 clasp push 실패
   - GitHub Actions `echo "$CLASP_JSON" > file` 처리 시 줄바꿈 처리 깨짐
   - **해결**: `{"scriptId":"...","rootDir":"."}` 한 줄로 압축해서 Secret에 박기
2. **`rootDir`은 `"."` 권장** (빈 문자열 `""`보다 안정적)
3. **clasprc.json은 multiline 그대로 OK** (clasp 인증 토큰. 줄바꿈 보존 필수)
4. **PowerShell vs cmd 차이**: `%USERPROFILE%` (cmd) ≠ `$env:USERPROFILE` (PowerShell). 직접 경로 `C:\Users\<user>\.clasprc.json` 권장
5. **clasp push --force** = 콘솔 변경 무시하고 강제 덮어쓰기. **다른 task가 콘솔 직접 수정 중이면 작업 사라짐.** 책임 분담 표 엄수
6. **Node.js 20 deprecation** (2026-06-16부터 강제 24): workflow의 `node-version: '20'` → `'24'`로 1줄 수정 필요 (그 전까지는 무시 가능)

### 멀티 브랜드 활성화 (KT/국민/진짜폰스팟 신설 시)
1. 새 Google 스프레드시트 + 새 Apps Script 프로젝트 생성
2. 새 Script ID 확보 → GitHub Secret 추가 (예: `CLASP_JSON_KT`)
3. workflow에 step 1개 추가 (`brands/kt/` 또는 별도 폴더):
   ```yaml
   - name: Push to Apps Script (KT)
     working-directory: brands/kt
     env:
       CLASP_JSON_KT: ${{ secrets.CLASP_JSON_KT }}
     run: |
       echo "$CLASP_JSON_KT" > .clasp.json
       clasp push --force
   ```
4. git push 1번 → 폰스팟 + KT 동시 배포

### 검증 결과 (2026-06-11)
- ✅ Workflow run #1 (자동 push 트리거) — 1차 실패 (CLASP_JSON multiline) → 한 줄 압축 후 #3 성공 27초
- ✅ Apps Script 콘솔에 자동 반영 확인
- ✅ 다른 task 영역 무영향 (ads/code/, cardnews/, shorts/, _docs/ 등 unstaged 그대로)

### 📊 B1 시트 read 인프라 (2026-06-15 추가)

**목적**: 클로드가 광고운영 관리대장 시트를 자유롭게 read. 본점 generator.html doGet과 충돌 없는 별도 프로젝트 = 멀티 브랜드 패턴 차용.

**구성**:
- 별도 Apps Script 프로젝트 **PhoneSpot Sheet Export** (Script ID 별도)
- 로컬 폴더 `apps_script_sheet_export/Code.js` + `appsscript.json`
- GitHub Secret `CLASP_JSON_EXPORT` (한 줄 압축 JSON)
- workflow step `Push to Apps Script (Sheet Export)` 추가
- 토큰 인증 `EXPORT_TOKEN` (Script Properties) + `_secrets/sheet_export_url.txt` + `_secrets/sheet_export_token.txt`
- Drive 폴더 `PhoneSpot Sheet Snapshots` (ID `1M-w-Dx0oFAw8Bieq9hwiF17E-6BvWM1k`)
  - 매일 03:00 자동: 30탭 → `<탭명>.json` + `__meta.json` + `__headers.json` (전체 탭 첫 5행 한 파일)
  - `setupExportTrigger()` 1회 실행으로 트리거 등록

**클로드 read 흐름**:
1. **작은 파일** (< 30KB) = Drive MCP `read_file_content` 한 번에 read
2. **큰 파일** (메타_통합 137KB / 네이버_통합 330KB / GA4_자동 230KB) = 토큰 한계 초과 → `__headers.json` 단일 파일로 헤더 + 첫 5행 한 번에 read (27KB)
3. **실시간 호출** (사용자 PC) = `<URL>?token=...&sheet=<name>` 으로 시트 1개 JSON

**★ 함정**:
- Anthropic workspace proxy = `script.google.com` allowlist 차단 (`X-Proxy-Error: blocked-by-allowlist`)
  → 클로드 web_fetch 직접 호출 ❌
  → **Drive snapshot으로 우회 = 영구 해결책**
- 큰 파일 = `__headers.json` 전용 모델로 토큰 한계 우회
- Apps Script API 토글 OFF면 첫 push 실패 ("User has not enabled the Apps Script API") → https://script.google.com/home/usersettings → 토글 ON
- web app 배포 시 "본인 인증 + 누구나 접근" 모드 (URL+토큰 없으면 거부)

**셋업 검증 결과** (2026-06-15):
- workflow #5 (`c393ad4`) 실패 (Apps Script API OFF) → 토글 ON 후 #6 성공 23초
- 첫 `exportAllSheetsToDrive` 실행: 30탭 60초
- `__headers.json` 추가 후 재실행: 80초 (오버헤드 20초)
- 클로드 read 검증: ✅ Drive MCP로 작은 파일 전부 read, `__headers.json`로 큰 파일 헤더 파악

---

### 🔔 실패 알림 셋업 (2026-06-15 추가)
workflow 실패 시 (CLASPRC_JSON 만료, clasp push 에러, Node 버전 deprecation 등) **텔레그램 자동 알림**. 카드뉴스용 봇 재활용.

- **workflow step**: `Notify Telegram on failure` (`if: failure()` — 직전 step 실패 시만 트리거, 성공 시 발송 X = 노이즈 차단)
- **GitHub Secrets 필요 (등록 완료)**: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (값 = 로컬 `_secrets/telegram_token.txt`, `telegram_chat_id.txt`)
- **알림 내용**: 리포명 / 브랜치 / 커밋 SHA / 실행자 / Actions run 직링크
- **API**: `https://api.telegram.org/bot<TOKEN>/sendMessage`, URL-encoded text (`%0A` = 줄바꿈)
- **검증 방법**: workflow가 실패하도록 일부러 깨뜨림 (예: `clasp push --force` 직전 `exit 1` step 추가) → 텔레그램 알림 도착 확인 → 원복. 별도 검증 안 해도 첫 실패 시 자동 작동.
- **확장**: 멀티 브랜드 step 추가 시 알림 step은 그대로 — 모든 step의 failure를 캐치. 별도 작업 없음.

성공 알림은 안 박음 (매번 알림 = 노이즈). 필요 시 별도 step 추가 가능.

---

---

## 한 줄 요약

코드 = 공용 (`_shared/`) / 데이터·설정 = 브랜드별 (`brands/<brand>/`) / 단일 진실 원천 = GitHub repo / Apps Script ↔ GitHub 동기화 = clasp.

---

## 핵심 원칙 4가지

1. **코드 = 공용** — 1곳 수정 → 모든 브랜드 자동 반영
2. **데이터/설정 = 브랜드별** — 시트 ID, API 토큰, 매장명 분리
3. **GitHub repo = 단일 진실 원천** — 모든 변경 git log로 추적
4. **자산은 git 비전파** — CLAUDE.md STEP 0/7 룰 그대로 (`images/`, `output/`, `node_modules/`, `_secrets/` 등)

---

## 폴더 구조

```
phonespot_cardnews/                     ← GitHub repo (현재 그대로)
│
├── _shared/                            ← ★ 공통 코드 (모든 브랜드 사용)
│   ├── apps_script/                    ← Google Sheets 자동화
│   │   ├── Code.gs
│   │   ├── meta-sync.gs
│   │   ├── naver-sync.gs
│   │   ├── youtube_sync.gs
│   │   └── generator.html
│   ├── cardnews/                       ← 카드뉴스 코드 (스크립트/템플릿)
│   │   ├── webui/
│   │   ├── scripts/
│   │   ├── templates/
│   │   └── run_pngs.bat
│   ├── shorts/                         ← 영상 코드
│   │   ├── promo/
│   │   └── promo_ai/
│   └── automation/                     ← listener / outbox
│
├── brands/                             ← ★ 브랜드별 분리
│   ├── phonespot/                      ← 폰스팟 본점 (현재)
│   │   ├── config.json                 ← 시트ID, 매장명, 토큰 ref
│   │   ├── .clasp.json                 ← Apps Script ID (gitignore)
│   │   ├── articles/                   ← 카드뉴스 기사 (git 전파)
│   │   ├── images/                     ← 카드 이미지 (gitignore, Drive sync)
│   │   ├── output/                     ← 렌더 결과 (gitignore)
│   │   └── _secrets/                   ← API 키 (gitignore)
│   ├── kt/                             ← KT다이렉트샵
│   ├── kookmin/                        ← 국민인터넷
│   └── phonespot_real/                 ← 진짜 폰스팟 (판매점 가입형)
│
├── ads/                                ← 가이드 (공용)
├── _docs/                              ← 매뉴얼 (공용)
├── CLAUDE.md                           ← 부트스트랩 (공용)
└── scripts/                            ← 배포/유틸
    ├── push-all-apps-script.sh         ← 모든 브랜드 Apps Script 동시 배포
    ├── render-cardnews.sh              ← brand 지정 카드 렌더
    └── sync-images.sh                  ← Drive 일러스트 허브 sync
```

---

## 업데이트 워크플로우 — 시나리오 3가지

### 시나리오 1 — 공통 코드 수정 (모든 브랜드 반영)
```bash
# Apps Script 에디터 또는 로컬에서 수정
cd _shared/apps_script
clasp pull                              # Apps Script 에디터 수정 시
cd ../..
git commit -m "메타: 신규 필터 추가"
git push
./scripts/push-all-apps-script.sh       # N개 브랜드 Apps Script 동시 배포
```

### 시나리오 2 — 브랜드 전용 데이터 (카드뉴스 기사 추가)
```bash
vim brands/phonespot/articles/065_news_topic.json
git commit -m "폰스팟: 65번 기사"
git push
# Apps Script 배포 불필요
```

### 시나리오 3 — 브랜드별 운영 (카드뉴스 렌더)
```bash
./scripts/render-cardnews.sh phonespot 65
./scripts/render-cardnews.sh kt 12
```

---

## 다른 task 충돌 방지 — 책임 분담 (2026-06-15 갱신)

| 파일/폴더 | 책임자 | 비고 |
|---|---|---|
| `_shared/apps_script/generator.html` | 다른 task (Claude 광고생성기) | 광고 생성기 UI |
| `_shared/apps_script/Code.gs`, `meta-sync.gs`, `naver-sync.gs`, `youtube_sync.gs`, `danggn-sync.gs` | **광고운영 task** | 시트 자동화 코드 |
| **Phase 2~4 멀티 브랜드 셋업** (`_shared/` 폴더 분리, `brands/<brand>/`, workflow step 추가, KT/국민/진짜폰스팟 신설) | **★ 멀티 브랜드 task (별도, 2026-06-15 사장님 결정)** | 광고운영 task가 안 만짐 |
| `apps_script_sheet_export/` (B1 시트 read 인프라) | 광고운영 task | 별도 Apps Script 프로젝트 |
| `_shared/cardnews/`, `_shared/shorts/` | 영상 task / 코덱스 | 카드뉴스/영상 |
| `brands/<brand>/articles/` | 사용자 + Claude (기사작성 spec) | 콘텐츠 |
| `brands/<brand>/config.json` | 사용자 | 브랜드 설정 |

→ 같은 파일 동시 수정 금지. 충돌 시 git merge 또는 협의.

**Apps Script 콘솔 직접 수정 시 룰**: 수정 후 즉시 `clasp pull` + `git commit` (GitHub 어긋남 방지). 단 콘솔 직접 수정 ❌ (Phase 1 자동 배포 = force push로 덮어쓰임).

### ★ 멀티 브랜드 task 시작 명령 (2026-06-15 결정)

광고운영 task = 시트 관리 + GA4 매칭 + 자동화에 집중. **멀티 브랜드 (Phase 2~4) 작업은 별도 task로 분리.**

별도 클로드 세션 (다른 task) 시작 시 다음 명령으로 입장:

| 작업 시점 | 명령 (사장님 입력) |
|---|---|
| Phase 2 (`_shared/` 폴더 분리 + `brands/phonespot/` 셋업) | `ads/MULTI_BRAND_ARCHITECTURE.md 읽고 Phase 2 진행. _shared/ 폴더 분리 + brands/phonespot/ 셋업` |
| KT 시트 신설 | `KT다이렉트샵 멀티 브랜드 신설. ads/MULTI_BRAND_ARCHITECTURE.md "멀티 브랜드 활성화" 절차 + DISASTER_RECOVERY.md Bootstrap 시나리오 B 참고` |
| 국민인터넷 / 진짜폰스팟 신설 | 동일 패턴 (`<brand>` 자리에 brand 이름) |

별도 task가 처음 들어올 때 = 이 가이드 + `CLAUDE.md` STEP 8 2026-06-11 "Phase 1 셋업 완료" 섹션 자동 Read = 컨텍스트 인계 완성.

**광고운영 task (이 task)는 멀티 브랜드 폴더 절대 안 만짐.** 시트 관리 + GA4 매칭 + 자동화만 진행.

---

## 단계별 구현 — Phase 1~4

### Phase 1 — Apps Script만 멀티 브랜드 (1회 30분~1h)
- `_shared/apps_script/` 폴더 만들기 + 현재 코드 `clasp clone`
- `brands/phonespot/.clasp.json` 박기 (Script ID)
- `./scripts/push-all-apps-script.sh` 배치 스크립트 1개
- `.gitignore`에 `**/.clasp.json` + `**/.clasprc.json` 박기
- **첫 commit + push** — GitHub 백업 완료

**진입 조건**: 다른 task의 `generator.html` 작업 종료 (충돌 방지).

**완료 효과**: 코드 백업/이력 즉시 확보. KT/국민/진짜폰스팟 신설 시 `.clasp.json`만 추가하면 끝.

### Phase 2 — 카드뉴스 멀티 브랜드 (다음 작업)
- `cardnews/articles/` → `brands/<brand>/articles/` 이관
- 패널 코드 (`server.py`, `webui/app.py`)가 `brand` 파라미터 받도록 수정
- 렌더 출력도 `brands/<brand>/output/`

### Phase 3 — 영상 멀티 브랜드 (그 다음)
- `shorts/` 도 동일 패턴
- `CODEX_VIDEO_DESK/`도 brand 분기

### Phase 4 — 자동화 멀티 브랜드 (마지막)
- telegram listener, outbox, run_pngs도 brand 분기

---

## 정직한 한계 + 주의사항

### 잘 되는 것 ✅
- Apps Script 코드 멀티 배포 — clasp 1줄
- 카드뉴스 기사 JSON / 가이드 / 매뉴얼 — git 전파 (이미 그래도 동작)
- 코드 백업 / 변경 이력 / 롤백

### 어려운 것 ⚠️
- **카드 이미지** (1GB+) — git 비효율. Drive 데스크톱 sync 유지 (STEP 0 룰 그대로)
- **node_modules / 임베딩 DB / `_secrets/`** — git 비전파 (각 PC에서 SETUP 실행)
- **시트 데이터** — git에 없음 (Google에 있음). 코드만 GitHub
- **Apps Script 동시 수정 충돌** — 다른 task가 같은 파일 만지면 머지 필요

### 위험 신호
- Apps Script 콘솔 수정 후 `clasp pull` 안 하면 GitHub 어긋남
- 다른 사람도 동시 수정 시 누군가 덮어쓰기
- **해결**: 책임 분담 표 명시 (위 표) + 콘솔 수정 시 즉시 sync 룰

---

## 운영 비용 비교

| 항목 | 현재 (수동 복붙) | Phase 1 후 |
|---|---|---|
| 코드 수정 후 1개 브랜드 반영 | Apps Script 저장 (즉시) | Apps Script 저장 + `clasp pull` + git commit (3줄) |
| 코드 수정 후 4개 브랜드 반영 | 4번 수동 복붙 (실수 위험 큼) | `./push-all-apps-script.sh` 1줄 |
| 버그 발생 시 롤백 | 사실상 불가 | `git revert` + clasp push 1분 |
| 코드 백업 | ❌ | ✅ GitHub 영구 보존 |

---

## 다음 step (확정 시)

1. Node.js 설치 확인 (`node --version`)
2. clasp 설치 + 로그인
3. `_shared/apps_script/` 폴더 + `clasp clone` (현재 Apps Script Script ID)
4. `.gitignore` 박기
5. 첫 `clasp pull` + git commit + push
6. `brands/phonespot/.clasp.json` 분리 박기 (옵션)
7. `./scripts/push-all-apps-script.sh` 배치 스크립트 작성 (브랜드 신설 시 1줄씩 추가)

진행은 다른 task 작업 종료 후 결정.

---

작성: 2026-06-11

---

## 멀티 브랜드 — 하드코딩 감사 + 설계 결정 (2026-06-28)

### 사장님 결정
- **브랜드마다 별도 구글계정 전부** (폰스팟 / KT폰샵 / 향후 국민·진짜폰스팟 각자 계정+시트+Apps Script).
- **확장 구조 = config 참조 + 편집가능** (하드코딩 X). 비밀값만 Script Property, 나머지 브랜드설정은 편집가능한 `_설정` 시트로.

### 하드코딩 브랜드 의존값 감사 (apps_script/)
**A. 코드 수정 필요 (config로 분리)**
1. ★ `Code.js:8 GA4_PROP_ID='534396517'` (폰스팟 GA4 속성) → 브랜드별. **미수정 시 KT가 폰스팟 GA4 읽음.**
2. ★ `youtube_sync.js:26 SHEET_ID='1tCG…'`(3곳 openById) → `SpreadsheetApp.getActive()`. **미수정 시 KT가 폰스팟 유튜브 시트에 씀.**
3. ★ KT필터 `meta-sync.js:259 ['KT','다이렉트샵'] 제외` + `naver-synce.js:304 NAVER_KT_FILTER` → 폰스팟=KT제외 / KT폰샵=KT만(반전). 브랜드별 필터 모드.
4. Drive 인사이트 폴더 `'phonespot_cardnews_state'` (meta-sync:1694, youtube_sync:28) → 브랜드 접두사.
5. 표시 "폰스팟" 리터럴 (Code.js 메뉴/타이틀) → 브랜드명(선택).

**B. Script Property = KT 프로젝트에 값만 등록(코드 수정 X, 자동 분리)**
META_TOKEN·META_AD_ACCOUNT_ID / NAVER_API_LICENSE·NAVER_SECRET_KEY·NAVER_CUSTOMER_ID / GOOGLE_ADS_*(6) / INSTAGRAM_BUSINESS_ID / DANGGN_UTM_SOURCE / TELEGRAM_BOT_TOKEN·TELEGRAM_CHAT_ID / TARGET_CPL·BENCHMARK_TERMS / GEMINI_API_KEY·APIFY_TOKEN.

**C. 계정 묶임**: `youtube_sync.js mine:true` = 실행 계정의 채널 → 별도 구글계정이면 자연 분리(결정과 일치).

### 설계: config 하이브리드 (참조+편집)
- **비밀값(토큰·API키)** = Script Property 유지(시트 노출 금지, 보안).
- **비밀 아닌 브랜드설정**(BRAND명, GA4_PROP_ID, KT필터모드, 인사이트폴더, TARGET_CPL 등) = 각 브랜드 시트의 **`_설정` 탭**(편집가능)에 두고 코드가 참조. 폴백=현 폰스팟 기본값(무회귀).
- 효과: 브랜드 추가/변경 = **시트 값만 수정**(코드·Apps Script 설정 안 건드림) → 확장 용이.

### ★ 별도 계정의 배포 함의 (중요)
- 계정마다 clasp 인증이 달라 GitHub Actions에 **계정별 clasprc 필요**: `CLASPRC_JSON`(폰스팟) + `CLASPRC_JSON_KT`(KT) + 각 `CLASP_JSON_*`(scriptId). workflow에 브랜드 step 추가.
- 또는 배포계정을 각 시트 편집자로 공유(바운드 스크립트라 까다로움) — 계정별 clasprc 권장.

### 다음 단계 (미착수, 컨펌 후)
1. `_설정` 탭 스키마 확정 → 2. 코드 A 5개를 config 참조+폴백으로 리팩터(폰스팟 무회귀 검증) → 3. KT 계정/시트/scriptId/secret 셋업 → 4. workflow KT step.

---

## KT폰샵 셋업 진행분 (2026-06-30, 중단 지점)

### 결정·현황
- **모델 = 완전 별도(A)**: KT폰샵은 별도 사업자로 메타·네이버 광고계정 **신규 가입**, **별도 GA4 속성 신규 생성**, **별도 웹사이트 랜딩**. 폰스팟과 데이터·계정 완전 분리.
- **사본 생성됨**: `KT폰샵 광고운영 관리대장` (시트ID `1M0wgjlihpAYMS8KmR-ho3HIJL0skybP0OJYbnvm79nM`). ★ 소유자 = **313jongmin@gmail.com (폰스팟과 동일 계정)** — 별도 구글계정 아님(메인 계정 내 사본). 광고/GA4 계정만 별도, 구글 소유계정은 공유.
  - **함의**: 같은 계정이라 **clasp 인증(CLASPRC_JSON) 공유** → KT 배포에 CLASPRC_JSON_KT 불필요, `CLASP_JSON_KT`(=KT .clasp.json 한 줄)만 추가.
- **KT scriptId** = `19mLDjT-A2jk5oE3mTAZioYuKT2gGj_yEQT8ZuyGddA-hvA5uhqhS7Itj`.

### 코드 도구 (멀티브랜드, Code.js 신설 — 2026-06-30)
- `setupBrandConfigSheet()` (메뉴 🏢 _설정 탭 생성/갱신): `_설정` 키-값 탭 생성, **기존 값 보존**(재실행 안전), 값칸 노랑.
- `clearBrandDataForTemplate()` (메뉴 🧹 새 브랜드 빈 템플릿화): 사본에서 데이터행만 비움(헤더·우측 월별/요약 블록·대시보드 수식 보존), (구) 잔재 탭 삭제. **확인 다이얼로그 필수, 폰스팟 원본에서 금지.** 비우는 탭별 [시작행,끝열]은 함수 내 LIST 참조(우측블록 보호).
- 배포: `.github/workflows/deploy-apps-script.yml`에 **"Push to Apps Script (KT폰샵)" step 추가** — 폰스팟 본점 push 뒤, apps_script 코드를 KT scriptId(.clasp.json=CLASP_JSON_KT)로 한 번 더 clasp push. → git push 1번 = 폰스팟+KT 동시 배포.

### KT `_설정` 값 (확정 + 미완)
BRAND_NAME=KT폰샵 / CARRIER_FILTER_MODE=exclude+키워드空(=전부통과, none과 동일동작) / INSIGHTS_DRIVE_FOLDER=kt_cardnews_state / DANGGN_UTM_SOURCE=daangn / TARGET_CPL=30000.
**미완 = GA4_PROP_ID 비어있음.**

### ★ 함정 / 중단 이유 (다음 세션 필독)
- **GA4_PROP_ID 비우면 폴백이 폰스팟 GA4(534396517)** → KT가 폰스팟 GA4를 읽음. **KT GA4 속성 생성 전까지 KT에서 fetchGA4Daily 실행·GA4/전체새로고침 트리거 설정 금지**(폰스팟 GA4 오염). KT GA4 만들고 속성ID 입력 후에 GA4 sync·트리거 ON.
- 다른 채널(메타·네이버)은 토큰 없으면 0이라 위험 없음 — GA4만 폴백 때문에 주의.

### 남은 일 (재개 시)
1. ○ `CLASP_JSON_KT` GitHub Secret 등록(한 줄) + workflow push → KT step 초록 확인(= KT에 현재 코드 배포).
2. ○ KT 사본에서 🧹 빈 템플릿화 실행.
3. ○ KT 사업자 메타·네이버 계정 가입 → 토큰 KT Script Property 등록(채널별로 생기는 대로).
4. ○ **KT GA4 속성 생성** → _설정 GA4_PROP_ID 입력 + KT 웹사이트 GA4/GTM 심기 → 그 후 GA4 sync·트리거 ON.
정본 = 이 파일 + `_docs/SYSTEM_MAP.md` 멀티브랜드 항목.
