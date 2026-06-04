# KT다이렉트샵 시트 셋업 — 폰스팟 사본 복제 가이드

> 폰스팟 시트(`1tCGFfu2FbGo1XbigaYPptlSbD-7Tj3PLnYH0_o9g5jI`) 사본 → KT다이렉트샵용 정리. 약 30분.

---

## 1단계 — 폰스팟 시트 사본 만들기 (3분)

1. 폰스팟 광고운영 관리대장 열기
2. **파일 → 사본 만들기**
3. 사본 이름: `KT다이렉트샵 광고운영 관리대장`
4. 위치: Drive 적절한 폴더 (회사 폴더 권장)
5. **"공유 권한 복사" 체크 해제** (KT 따로 권한 관리)
6. 사본 만들기 → 새 시트 열림
7. **시트 ID 복사** → `ads_kt/README_FOR_AI.md`의 "Google Sheets" 줄에 박기
   - URL `https://docs.google.com/spreadsheets/d/{여기가_시트_ID}/edit`

---

## 2단계 — Apps Script 코드 정리 (10분)

새 시트에서 **확장 프로그램 → Apps Script** 열기 → Code.gs는 사본으로 그대로 있음.

### 2-1. 상수 교체 (코드 맨 위)

찾기:
```javascript
const GA4_PROP_ID = '534396517';
```

→ KT용 GA4 새로 만든 후 그 Property ID로 교체. **5단계** 끝나면 다시 박을 것.

`INQUIRY_SHEET`, `KAKAO_REPORT_START_COL` 등 다른 상수는 일단 그대로 (시트 구조 비슷하므로).

### 2-2. 함수 제거·수정

| 함수 | 처리 |
|------|------|
| `fetchGA4Daily` / `fetchGA4Backfill` / `importGA4` | 유지 (GA4 ID만 위에서 바뀌면 자동 적용) |
| `updateKPISummary` | **수정** — 채널 목록에서 당근/카카오 제거, KT 운영 채널만 |
| `updateChannelMatrixWithGA4` | **수정** — 동일. 채널 정의 배열에서 메타·구글·네이버만 (또는 KT 운영 채널) |
| `updateSNSReport` | **유지** — 단 운영 안 하는 SNS 채널 제거 |
| `repairSNSMonthlySummaries` | 유지 |
| `updateKakaoInquiryCoverage` | **유지** (KT도 카톡 문의 받을 수 있음) — 카톡 비즈채널 따로면 적절 |
| `addTimeSeriesChart` | 유지 |
| `weeklyBackup` | **추가** (폰스팟과 동일 패턴) — Drive 폴더명만 `KT다이렉트샵_백업`으로 |

### 2-3. 시티마켓·리틀리 관련 제거

검색해서 다 제거:
- `citymarket_click` (이벤트)
- 리틀리 시트 참조 (`'리틀리'!`)
- `linkurl contains "citymarket"` 같은 GA4 측정

KT다이렉트샵은 시티마켓/리틀리 안 씀.

---

## 3단계 — 시트 탭 정리 (10분)

새 시트(KT다이렉트샵)에서:

### 3-1. 채널 시트 정리

| 탭 | 처리 |
|----|------|
| 메타 | 유지 (이름 그대로) — 단 데이터 클리어 |
| 구글 | 유지 — 데이터 클리어 |
| 네이버 | 유지 — KT는 네이버 검색 비중 큼 |
| 카카오 | 일단 유지 — 운영 결정 후 삭제 가능 |
| 당근 | **삭제** (KT 공식은 당근 광고 못 함) |

각 채널 시트의 데이터(행 4~ 일별 데이터) 다 클리어. 헤더만 남김.

### 3-2. SNS 시트

| 탭 | 처리 |
|----|------|
| 스레드 / 인스타 / 유튜브 / 틱톡 | 일단 유지 — 운영 결정 후. 단 데이터 클리어, 폰스팟 콘텐츠 다 삭제 |

### 3-3. 기타 시트

| 탭 | 처리 |
|----|------|
| 문의접수 | 데이터 클리어 (헤더 + H:Q 카톡 리포트 헤더 유지) |
| 결제내역 | 데이터 클리어 |
| 리틀리 | **시트 삭제** |
| GA4_자동 | 데이터 클리어 (행 5~). 새 GA4 연결 후 채워짐 |
| UTM_생성기 | 유지. 단 source 드롭다운에서 daangn 제거, kt_official 같은 KT 전용 추가 |
| 📚 참조 | 폰스팟 내용 다 삭제 → KT 가이드라인 문서로 교체 |
| 통합대시보드 | 그대로 (함수가 재구성해줌) |
| 추세 | 그대로 |

---

## 4단계 — 통합대시보드 재구성 (3분)

`🛠 폰스팟 운영` 메뉴 (이름은 그대로 둬도 됨) 또는 함수 셀렉터에서:

1. `updateKPISummary` 실행
2. `updateChannelMatrixWithGA4` 실행 (단 채널 배열 수정 후)
3. `updateSNSReport` 실행
4. `addTimeSeriesChart` 실행

→ KT다이렉트샵용 빈 대시보드 완성. 데이터 들어오면 자동 채워짐.

---

## 5단계 — GA4 새 속성 생성 (10분)

1. https://analytics.google.com/ 접속 (313jongmin@gmail.com 로그인)
2. 좌하단 **관리** → **계정 만들기** (또는 기존 계정 안에 새 속성)
3. 속성 이름: `KT다이렉트샵`
4. 데이터 스트림 추가 → 웹
   - URL: `https://kt-directshop.com/`
   - 스트림 이름: KT다이렉트샵
5. **측정 ID** 복사 (`G-XXXXXXXX`)
6. KT 사이트에 측정 ID 박기:
   - **방법 A**: KT 본사가 GTM 관리하면 GTM에 요청 (시간 걸림, KT 본사 협조 필요)
   - **방법 B**: 시티마켓처럼 dual-tracking — 기존 KT GTM에 우리 측정 ID 추가 요청
   - **방법 C**: KT 본사가 거부하면 → 추후 자체 랜딩 페이지에서 측정 (단기엔 GA4 데이터 X)
7. Apps Script Code.gs의 `GA4_PROP_ID` 를 새 Property ID로 교체

---

## 6단계 — 광고 계정 셋업 (별도 작업)

각 광고 플랫폼에서 새 비즈니스 계정 생성:

| 채널 | 셋업 |
|------|------|
| 메타 | Business.facebook.com → 새 비즈니스 계정 → KT다이렉트샵 광고 계정 |
| 구글 | ads.google.com → 새 광고 계정 |
| 네이버 | ads.naver.com → 새 광고 계정 |

→ 너네 권한 명시. 사용자 정보 보호 신경.

---

## 7단계 — 첫 광고 시작 시

1. UTM_생성기 탭에서 UTM 박기 (source=meta, medium=cpc, campaign=kt_promo_X 등)
2. 광고 플랫폼에 UTM 박힌 URL 등록
3. 첫 행 (날짜만이라도) 채널 시트에 입력
4. 2~3일 후 GA4_자동에 데이터 들어오는지 확인

---

## 셋업 후 추가 작업

| 항목 | 시점 |
|------|------|
| MANUAL.md 작성 — KT 가이드라인 + 운영 룰 | 셋업 후 1일 |
| 사전승낙서 추적 시트 | 셋업 후 1주 (KT 본사 발급 사전승낙서) |
| weeklyBackup 함수 추가 + 트리거 | 셋업 직후 |
| Looker Studio 통합 보고서 (폰스팟 + KT다이렉트샵) | 두 시트 안정화 후 |

---

작성: 2026-05-30
