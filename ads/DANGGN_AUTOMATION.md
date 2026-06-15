# 당근 자동화 가이드 (2026-06-15 신설)

> 당근 광고는 **공식 API 없음** = 운영 데이터(노출/클릭/지출)는 사장님이 수기 입력. **GA4 데이터만 SUMIFS 수식으로 자동 매칭.**
>
> 네이버_sync 패턴 그대로 차용. 단 17컬럼으로 단순화 (메타_통합 19컬럼에서 캠페인ID/광고그룹ID 컬럼 2개 제외, 당근은 API 없으니 ID 의미 없음).

## 시트 구조 (`당근_통합`)

| 열 | 컬럼 | 입력 |
|---|---|---|
| A | 날짜 | 수기 |
| B | 캠페인명 | 수기 (자유) |
| C | 광고그룹명 | 수기 (★ 당근_UTM_매핑 시트와 일치해야 GA4 매칭됨) |
| D | 노출 | 수기 |
| E | 클릭 | 수기 |
| F | 지출 | 수기 |
| G | CTR | 자동 수식 `=E/D` |
| H | CPC | 자동 수식 `=F/E` |
| I | GA4세션 | 자동 매칭 (SUMIFS) |
| J | 카톡클릭 | 자동 매칭 |
| K | 전화클릭 | 자동 매칭 |
| L | 시티마켓 | 자동 매칭 |
| M | 카톡전환률 | 자동 수식 `=J/I` |
| N | 카톡당CPC | 자동 수식 `=F/J` |
| O | 문의수 | 수기 |
| P | 개통수 | 수기 |
| Q | 메모 | 수기 |

## UTM 매핑 시트 (`당근_UTM_매핑`)

| 열 | 컬럼 |
|---|---|
| A | 당근 광고그룹명(한글) — `당근_통합` C열과 일치 |
| B | utm_campaign(영문) — GA4 sessionCampaignName 값 |
| C | 첫 발견일 |
| D | 상태 |
| E | 메모 |

→ 사장님이 광고그룹 신설 시 **이 시트에 1줄 수기 추가**. API 없으니 자동 발견 X.

## GA4 매칭 키 (SUMIFS)

```
GA4_자동!A열(date)              = 당근_통합!A열 (YYYYMMDD 텍스트로 변환)
GA4_자동!B열(sessionSource)     = DANGGN_UTM_SOURCE (Script Property, 기본 "danggn")
GA4_자동!D열(sessionCampaignName) = 당근_UTM_매핑 VLOOKUP (C열 광고그룹명 → 영문 utm_campaign)
GA4_자동!E열(eventName)         = session_start / kakao_chat_click / phone_click / citymarket_click
```

## 사장님 1회 셋업

1. 시트 메뉴 **🥕 당근 자동화 → 🆕 시트 신설 / 헤더 갱신** → 시트 2개 자동 생성
2. Apps Script 콘솔 → 프로젝트 설정 → 스크립트 속성 → `DANGGN_UTM_SOURCE` 등록 (GA4에서 잡히는 정확한 값, 예: `danggn`)
3. 메뉴 **🔑 utm_source 값 확인** → 등록값 검증
4. 메뉴 **⏰ 당근 Daily Trigger 설정 (02:30)** → 매일 자동 실행
5. 시트에 첫 데이터 입력 → 메뉴 **🔄 당근_통합 GA4 매칭 (오늘)** 수동 검증

## 운영 흐름 (매일)

1. 사장님이 당근 광고관리자에서 노출/클릭/지출 확인 → `당근_통합` D~F에 수기 입력 + A 날짜 + C 광고그룹명
2. 새 광고그룹 신설 시 → `당근_UTM_매핑`에 1줄 추가 (한글 ↔ 영문)
3. 매일 02:30 `syncDanggnGA4` 자동 실행 → G/H/M/N 수식 + I~L GA4 매칭
4. 통합대시보드 매트릭스에 당근_통합 F열(지출) 자동 합산 (★ 메타_통합 H열과 위치 다름 = `updateChannelMatrixWithGA4` 분기 필요, 미구현 = TODO)

## 함정

- **`DANGGN_UTM_SOURCE` 미등록 또는 GA4 실제 값과 다름** → 매칭 0건. 시트 메뉴 "🔑 utm_source 값 확인" 으로 검증.
- **광고그룹명이 `당근_UTM_매핑`에 없음** → VLOOKUP 빈 결과 → 매칭 0. 메뉴 "🔍 미매핑 광고그룹 보기" 로 진단.
- **17컬럼 단순화** = 통합대시보드 합산 시 지출 위치가 메타_통합(H)과 다름(F). `Code.gs updateChannelMatrixWithGA4` 분기 추가 필요 (미구현).
- **옛 "당근" 시트는 그대로 유지** = 수기 영업 일지용. 새 당근_통합과 별개. 통합대시보드 합산 시 둘 다 합산되지 않도록 1개만 선택 필요.

## 코드 위치

- `apps_script/danggn-sync.js` (본점 Apps Script, GitHub Actions 자동 배포)
- 메뉴 호출 = `apps_script/Code.js` onOpen 마지막 줄 `buildDanggnSyncMenu_()`
- 트리거 = `setupDanggnTrigger()` (콘솔에서 1회 실행)

## 정본 참조

- 시트 구조 = `ads/data/sheet_structure.md` 2026-06-15 갱신 표
- 변경 이력 = `CLAUDE.md` STEP 8 2026-06-15 세션 3
- 시스템 맵 = `_docs/SYSTEM_MAP.md` G단원 2026-06-15 세션 3
- B1 시트 read 인프라 = `ads/MULTI_BRAND_ARCHITECTURE.md`
