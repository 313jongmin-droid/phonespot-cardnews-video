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

## 다른 task 충돌 방지 — 책임 분담

| 파일/폴더 | 책임자 | 비고 |
|---|---|---|
| `_shared/apps_script/generator.html` | 다른 task (Claude 광고생성기) | 광고 생성기 UI |
| `_shared/apps_script/Code.gs`, `meta-sync.gs`, `naver-sync.gs`, `youtube_sync.gs` | 사용자 + 이 task (광고운영) | 자동화 코드 |
| `_shared/cardnews/`, `_shared/shorts/` | 영상 task / 코덱스 | 카드뉴스/영상 |
| `brands/<brand>/articles/` | 사용자 + Claude (기사작성 spec) | 콘텐츠 |
| `brands/<brand>/config.json` | 사용자 | 브랜드 설정 |

→ 같은 파일 동시 수정 금지. 충돌 시 git merge 또는 협의.

**Apps Script 콘솔 직접 수정 시 룰**: 수정 후 즉시 `clasp pull` + `git commit` (GitHub 어긋남 방지).

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
