# ads/ — 폰스팟 광고운영 관리 허브

> **AI 진입점.** 광고운영 관련 작업을 시작할 때 가장 먼저 읽는 파일.
> 마지막 갱신: 2026-06-15 (B1 시트 read 인프라 + 당근 자동화 + Phase 1 + Actions 알림)
> 옛 갱신: 2026-06-12 (광고 소재 생성기 대규모 리팩 + Apify 벤치마크 합류)

## 🚀 첫 진입 시 (다른 클로드 세션)

종민 명령이 "광고 소재" / "카피 생성" / "generator" / "벤치마크" / "Apify" 관련이면:

1. **`IMPLEMENTATION_GUIDE_2026-06-09.md` 먼저 읽기** — 단일 진입점, §6 함수 인덱스 + §12 디자인 토큰 + §14 다음 작업 후보
2. `ads/code/apps_script/generator.html` 상단 100줄 + `styles.html` (디자인 시스템 파악)
3. `ads/code/apps_script/meta-sync.gs` — Apify·벤치마크 함수 (815라인 이후)

종민 명령이 "관리대장" / "메타 자동화" / "KPI" / "GA4" 관련이면 (기존):

1. 이 파일 (`README_FOR_AI.md`)
2. `META_AUTOMATION.md` (§12 옵션 C는 폐기 마커, 무시)
3. `code/apps_script/Code.gs` + `meta-sync.gs`

## 종민 사용 패턴 (메모)

- 짧은 명령 ("진행", "B-4 보자", "이대로 마무리") 즉시 작동
- 정직한 한계·옵션 정량 비교 선호. 권장 강요 ❌
- 미사여구·과한 보고 ❌. "방금 한 일" 요약 ❌
- 옵션 제시 시 종민이 직접 선택
- 파일 손상 16회 경험. 큰 변경 시 통째 Write 권장

---

## 이 폴더는 뭐냐

폰스팟 브랜드의 **유료광고 + 운영 데이터 관리**가 모이는 모듈.
- 메인 클라우드 자산: **Google Sheets 「폰스팟 광고운영 관리대장」** + Apps Script
- 로컬 보관(이 폴더): 코드 백업, 운영 매뉴얼, 시트 구조 문서, 외부 채널 API 통합

부모 폴더(`phonespot_cardnews/`)의 다른 모듈(cardnews/shorts/automation/upload/)은 **건드리지 않음**. 정보가 필요하면 `bridges/`를 통해서만 읽음.

---

## 작업별 진입점

| 작업 | 첫 진입 |
|------|--------|
| **운영 매뉴얼 확인** (매일/주간 루틴, 트러블슈팅) | `MANUAL.md` |
| **메타 API + GA4 + UTM 매핑 자동화** ★ | `META_AUTOMATION.md` → `code/apps_script/meta-sync.gs` |
| **네이버 검색광고 자동화** ★ | `NAVER_AUTOMATION.md` → `code/apps_script/naver-sync.gs` |
| **당근 광고 자동화** (API 없음, 수기 + GA4 매칭) ★ 2026-06-15 신설 | `DANGGN_AUTOMATION.md` → `code/apps_script/danggn-sync.gs`. 시트 메뉴 🥕 당근 자동화 |
| **시트 read / 시트 구조 확인** (클로드용) ★ 2026-06-15 B1 셋업 | `apps_script_sheet_export/` 별도 프로젝트 + Drive 폴더 `PhoneSpot Sheet Snapshots` (매일 03:00 30탭 JSON + `__headers.json`). Drive MCP `read_file_content`로 read. 정본 = `MULTI_BRAND_ARCHITECTURE.md` |
| **UTM_매핑 시트 설계** | `data/utm_mapping_design.md` |
| **Apps Script 코드 수정/백업** | `code/apps_script/Code.gs` + `code/apps_script/functions.md` |
| **시트 구조·컬럼 확인** | `data/sheet_structure.md` |
| **카드뉴스/쇼츠 데이터 → 시트 동기화** | `bridges/README.md` |
| **새 광고채널 API 연동 추가** | `integrations/README.md` |
| **백업 복원** | `data/snapshots/` |

---

## 폴더 구조

```
ads/
├── README_FOR_AI.md       지금 이 파일
├── MANUAL.md              운영 매뉴얼 (사람용)
├── META_AUTOMATION.md ★   메타 API + GA4 + UTM 매핑 통합 가이드 (2026-06-05)
│
├── code/                  📝 시트 측 코드 (Apps Script)
│   └── apps_script/
│       ├── Code.gs            시트 자동화 (KPI/매트릭스/SNS)
│       ├── meta-sync.gs   ★   메타 API 자동 동기화 (campaign/소재/UTM)
│       ├── weeklyBackup.gs    주간 백업 트리거
│       ├── youtube_sync.gs    유튜브 데이터 동기화
│       └── functions.md       함수 인덱스
│
├── data/                  📊 시트 구조·스냅샷
│   ├── sheet_structure.md      각 시트 컬럼 정의·룰
│   ├── utm_mapping_design.md ★ UTM_매핑 시트 설계 (2026-06-05)
│   └── snapshots/              주기적 xlsx/csv 백업
│
├── bridges/               🔗 같은 폴더 내 다른 모듈과 정보 교환
│   ├── README.md
│   ├── from_cardnews.md   카드뉴스 발행 데이터 위치·스키마
│   ├── from_shorts.md     쇼츠 발행 데이터 위치·스키마
│   └── sync_sns_sheet.py  카드뉴스/쇼츠 → SNS 시트 자동 입력
│
└── integrations/          🌐 외부 광고 플랫폼 API
    ├── README.md          새 채널 추가 가이드
    ├── meta/              메타 광고 API (예정)
    ├── google_ads/        구글 광고 (예정)
    ├── naver/             네이버 검색광고 (예정)
    ├── kakao/             카카오 모먼트 (예정)
    ├── danggn/            당근 (API 없으면 수동 입력 가이드)
    └── ga4/               GA4 Data API (현재 Apps Script로 처리됨)
```

---

## ★ Apps Script 자동 배포 (Phase 1 셋업 완료 2026-06-11)

**옛 모델 (~2026-06-10)**: Apps Script 콘솔에서 직접 함수 수정 → 로컬 `apps_script/` 폴더와 drift → 사고(예: 인사이트 함수 누락 6/11) 재발 위험.

**새 모델 (Phase 1, 2026-06-11~)**: 로컬 PC에서만 코드 수정 → git push → GitHub Actions 자동 `clasp push --force` → 콘솔 자동 반영.

### 흐름
```
로컬 PC apps_script/ 수정
   ↓
git push origin main
   ↓
GitHub Actions (.github/workflows/deploy-apps-script.yml) 자동 trigger
   (paths: apps_script/**)
   ↓
clasp push --force → 폰스팟 본점 Apps Script 콘솔 자동 반영
   ↓
실패 시 → 텔레그램 알림 자동 (카드뉴스용 봇 재활용, 2026-06-15)
```

### 룰
1. **Apps Script 콘솔에서 직접 함수 수정 ❌** — 다음 git push 시 `clasp push --force`가 콘솔 변경 무시하고 덮어씌움 = 작업 사라짐. 코드 수정은 **로컬 PC `apps_script/` 폴더만**.
2. **로컬 PC만 push** (CLAUDE.md STEP 0). 노트북 = 크롬 원격 입구만, 부사수 PC = pull only.
3. **콘솔 코드 백업이 필요하면** `cd apps_script && clasp pull` (콘솔 → 로컬 동기화. 단 다른 task가 콘솔 수정 중이 아닌 시점만).
4. **다른 task와 영역 분리** = `apps_script/`(광고운영) / `cardnews/`(카드뉴스) / `shorts/`(영상). 동시 작업 시 영역 안 겹치면 git 충돌 거의 0.
5. **시크릿** = Apps Script `PropertiesService` (Google 클라우드 저장, PC 손상 무관) + GitHub Secrets (`CLASPRC_JSON`, `CLASP_JSON`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`).

### 정본
- **Phase 1 셋업 + 알림 + 멀티 브랜드 확장**: `ads/MULTI_BRAND_ARCHITECTURE.md`
- **머신 역할 표**: `CLAUDE.md` STEP 0 + `_docs/SYSTEM_MAP.md` F단원
- **재해 복구 + 시크릿 재발급**: `_docs/DISASTER_RECOVERY.md` (`_secrets/` 손실 시 재발급 절차)

### 자주 묻는 질문
- **Q: 콘솔에서 빨리 한 줄만 고치고 싶은데?** → ❌. 어차피 다음 push 때 덮어씌움. 로컬에서 수정 → push (1분).
- **Q: 실패 알림 안 옴?** → workflow 성공 시 알림 X (=정상). 실패 시만 트리거.
- **Q: 새 브랜드(KT 등) 추가?** → `ads/MULTI_BRAND_ARCHITECTURE.md` "멀티 브랜드 활성화" 섹션. workflow step + Secret 1줄씩 추가.

---

## 키 자원 (시트·계정·ID)

- **Google Sheets**: `1tCGFfu2FbGo1XbigaYPptlSbD-7Tj3PLnYH0_o9g5jI`
- **GA4 Property**: `534396517` / 측정 ID `G-2K74Y3FY65`
- **Google Ads 고객 ID**: `140-973-8298`
- **시티마켓 GTM**: `GTM-TMXR6VL9` (dual-tracking)
- 시크릿(토큰·API 키)은 부모 폴더의 `_secrets/`에 보관. **이 폴더에 시크릿 직접 저장 금지.**

---

## 실제 시트 데이터 확인 — Google Drive MCP 사용

이 폴더의 문서들(`MANUAL.md`, `functions.md`, `sheet_structure.md`)은 **스냅샷**. 실제 live 데이터는 시트에 있음.

### 시트 실시간 조회

Google Drive MCP가 연동되어있으면 새 세션에서:

```
ToolSearch("select:mcp__<drive-mcp-id>__read_file_content,mcp__<drive-mcp-id>__get_file_metadata")
→ read_file_content(fileId="1tCGFfu2FbGo1XbigaYPptlSbD-7Tj3PLnYH0_o9g5jI")
```

또는 Chrome MCP로 시트 열어서 직접 보기:
```
https://docs.google.com/spreadsheets/d/1tCGFfu2FbGo1XbigaYPptlSbD-7Tj3PLnYH0_o9g5jI/edit
```

### 작업 우선순위 (정확한 정보 필요할 때)

1. **시트 직접 조회** (live) — 광고 데이터·문의·결제·GA4 등 변동 데이터
2. **`Code.gs` 백업** (스냅샷) — 현재 배포된 Apps Script 코드. 시트의 Apps Script 에디터에서 최신본 확인 가능
3. **`functions.md` / `sheet_structure.md`** (가이드) — 구조·룰·인덱스. 자주 안 바뀜
4. **`MANUAL.md`** (운영) — 매일·주간·트러블슈팅 매뉴얼

→ **이 폴더 문서가 outdated되어도 시트가 진실의 원천.** 의심되면 시트 직접 조회.

---

## 작업 원칙

1. **단방향 의존** — `ads/`는 다른 모듈을 **읽기만**. 변경 X
2. **인터페이스 명시** — 다른 모듈에서 가져오는 데이터는 무조건 `bridges/` 통해. 직접 import X
3. **시크릿 분리** — API 키·토큰은 `_secrets/`에. 코드에 하드코딩 금지
4. **하네스 패턴** — 새 채널/모듈 추가 시 `integrations/<name>/` 표준 구조 따름 (auth.md / fetch.py / push.py / README.md)
5. **클라우드가 진실의 원천** — 코드/구조 문서는 시트와 일치해야 함. 불일치 시 시트가 우선

---

## 다른 모듈과의 관계

| 모듈 | 관계 |
|------|------|
| `cardnews/` | 카드뉴스 발행 시 SNS 시트(스레드/인스타) 자동 입력 → bridges/from_cardnews.md |
| `shorts/` | 쇼츠 발행 시 SNS 시트(유튜브/틱톡) 자동 입력 → bridges/from_shorts.md |
| `automation/` | 야간 daemon이 ads/ 동기화 스크립트도 실행 가능 |
| `_docs/` | _docs/는 카드뉴스/쇼츠 가이드 위주. 광고운영 가이드는 ads/에 자체 보관 |
| `_secrets/` | API 키·토큰 보관소 |
| `_backup/` | 큰 zip 백업. ads/data/snapshots/는 가벼운 일별 백업 |

---

폴더 생성: 2026-05-30
