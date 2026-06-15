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
GA4_자동!E열(eventName)         = session_start / kakao_chat_click / phone_click
                                  / citymarket_click + citymarket_arrival (합산, 2026-06-15)
```

★ **시티마켓 컬럼 = `citymarket_click` + `citymarket_arrival` 합산** (2026-06-15 갱신).
- `citymarket_click` = 리틀리 페이지에서 시티마켓 링크 클릭 시 발생 (메타·네이버 광고 → 리틀리 → 시티마켓 경로)
- `citymarket_arrival` = 시티마켓 페이지 도달 시 발생 (GTM `GTM-TMXR6VL9` 페이지뷰 트리거)
- **당근 광고 = 시티마켓 직접 유입 → click 발생 X → arrival로 잡힘**

## 사장님 1회 셋업

1. 시트 메뉴 **🥕 당근 자동화 → 🆕 시트 신설 / 헤더 갱신** → 시트 2개 자동 생성
2. Apps Script 콘솔 → 프로젝트 설정 → 스크립트 속성 → `DANGGN_UTM_SOURCE` = **`daangn`** 등록
   - ★ 정확한 값은 **`daangn`** (g 사이에 `aa`). `danggn` 아님 (옛 GA4 셋업 시 일부 오타 `danggn` 행 있지만 소수 = 무시)
   - 검증: GA4_자동 시트 B열에서 당근 광고 행 sessionSource 확인
3. 메뉴 **🔑 utm_source 값 확인** → 팝업에 `daangn` 보이면 OK
4. 메뉴 **⏰ 당근 Daily Trigger 설정 (02:30)** → 매일 자동 실행
5. 시트에 첫 데이터 입력 → 메뉴 **🔄 GA4 매칭 새로고침** 수동 검증

## GA4 sessionCampaignName 영문값 매핑 표 (실제 GA4 데이터 기준, 2026-06-15)

당근_UTM_매핑 시트의 B열(utm_campaign 영문)에 박을 값. **광고그룹명(한글)은 사장님 자유 입력**.

| 광고 유형 | GA4 sessionCampaignName (영문, 그대로 박기) |
|---|---|
| 가격확인 | `price_check` |
| 삼성 페스티벌 | `sm_festival` 또는 `sm_festa` |
| 갤럭시 A17 | `a17` |
| 무료폰 | `free_phone` |
| 지역광고 | `region` |
| 키즈폰 | `kids` |
| SA 광고 시리즈 (커뮤니티) | `sa_01`, `sa_02`, `sa_03`, `sa_04`, `sa_05` |

→ GA4_자동 시트 D열 검색으로 신규 광고 영문값 확인 가능.

## 운영 흐름 (매일)

1. 사장님이 당근 광고관리자에서 노출/클릭/지출 확인 → `당근_통합` D~F에 수기 입력 + A 날짜 + C 광고그룹명
2. 새 광고그룹 신설 시 → `당근_UTM_매핑`에 1줄 추가 (한글 ↔ 영문)
3. 매일 02:30 `syncDanggnGA4` 자동 실행 → G/H/M/N 수식 + I~L GA4 매칭
4. 통합대시보드 매트릭스에 당근_통합 F열(지출) 자동 합산 (★ 메타_통합 H열과 위치 다름 = `updateChannelMatrixWithGA4` 분기 필요, 미구현 = TODO)

## 함정

- **`DANGGN_UTM_SOURCE` 미등록 또는 GA4 실제 값과 다름** → 매칭 0건. ★ 정확한 값 = **`daangn`** (2026-06-15 검증). 시트 메뉴 "🔑 utm_source 값 확인" 으로 검증.
- **광고그룹명이 `당근_UTM_매핑`에 없음** → VLOOKUP 빈 결과 → 매칭 0. 메뉴 "🔍 미매핑 광고그룹 보기" 로 진단.
- **17컬럼 단순화** = 통합대시보드 합산 시 지출 위치가 메타_통합(H)과 다름(F).
- **옛 "당근" 시트와 당근_통합 이중 운영 위험**:
  - 현재(2026-06-15 셋업 직후): 옛 당근 시트(G열 지출)가 통합대시보드 매트릭스 합산. 당근_통합은 GA4 매칭만.
  - 사장님이 운영을 당근_통합으로 전환하면 `Code.js` `updateChannelMatrixWithGA4` 의 `channels` 배열에서 `당근` 행을 `당근_통합` + `spdCol:'F'` 로 갱신 필요 (현재 주석으로 박혀있음).
  - **이중 입력 절대 X** (양쪽에 같은 데이터 = 매트릭스 이중 합산).

## 코드 위치

- `apps_script/danggn-sync.js` (본점 Apps Script, GitHub Actions 자동 배포)
- 메뉴 호출 = `apps_script/Code.js` onOpen 마지막 줄 `buildDanggnSyncMenu_()`
- 트리거 = `setupDanggnTrigger()` (콘솔에서 1회 실행)

## 정본 참조

- 시트 구조 = `ads/data/sheet_structure.md` 2026-06-15 갱신 표
- 변경 이력 = `CLAUDE.md` STEP 8 2026-06-15 세션 3
- 시스템 맵 = `_docs/SYSTEM_MAP.md` G단원 2026-06-15 세션 3
- B1 시트 read 인프라 = `ads/MULTI_BRAND_ARCHITECTURE.md`
