# ads/ — 폰스팟 광고운영 관리 허브

> **AI 진입점.** 광고운영 관련 작업을 시작할 때 가장 먼저 읽는 파일.

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
