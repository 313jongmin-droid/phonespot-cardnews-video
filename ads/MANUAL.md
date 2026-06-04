# 폰스팟 광고운영 매뉴얼

> **사람용.** 매일/주간/월간 루틴 + 트러블슈팅. 너가 없어도 이 매뉴얼만 보고 운영 가능하도록 작성.

---

## 시트 바로가기

🔗 [폰스팟 광고운영 관리대장](https://docs.google.com/spreadsheets/d/1tCGFfu2FbGo1XbigaYPptlSbD-7Tj3PLnYH0_o9g5jI/edit)

---

## 매일 루틴 (5~10분)

### 1. 통합대시보드 확인
- 상단 KPI 카드: 이번달 광고비 / 30일 CPL / 30일 ROAS / 출처미상%
- 핵심 KPI 상세: 어제 / 7일 / 14일 / 30일 비교
- 채널 매트릭스 (E16 기간 드롭다운): 채널별 효율

### 2. 광고 관리자 → 시트 입력 (각 채널)

| 채널 | 광고 관리자 | 입력 위치 |
|------|------------|----------|
| 메타 | https://adsmanager.facebook.com/ | 메타 시트 A~H열 (날짜/노출/클릭/지출/문의수) |
| 구글 | https://ads.google.com/ | 구글 시트 동일 |
| 네이버 | https://ads.naver.com/ | 네이버 시트 동일 |
| 카카오 | https://moment.kakao.com/ | 카카오 시트 동일 |
| 당근 | https://business.daangn.com/ | 당근 시트 동일 |

> **입력 시 주의**: A=날짜, E=노출, F=클릭, G=지출, H=문의수. CTR/CPC/CPL은 자동 계산.

### 3. 문의접수 시트 — 새 카톡/전화 문의 추가
- A: 날짜 / B: 이름 / C: 개통여부(개통/불확실) / D: **유입채널** (필수!)
- 유입채널 표준값: 메타 / 구글 / 네이버 / 카카오 / 당근 / 인스타 / 스레드 / 뽐뿌 / 지인 / 불확실

### 4. 결제내역 — 광고비 충전 시 입력
- A: 날짜 / B: 채널 / C: 내용 / D: 비용 / E: 결제수단

---

## 주간 루틴 (월요일 30분)

1. **`🛠 폰스팟 운영` 메뉴 → `⚡ 전체 새로고침`** 실행
2. 채널 매트릭스 E16 = `최근 7일` 로 변경 → 채널별 효율 확인
3. 추세 시트 → 30일 일별 광고비 라인차트 → 변동 패턴 점검
4. 평가 컬럼 🔴 비효율 채널 → 광고 소재/타겟팅 점검

---

## 월간 루틴 (월초)

1. 결제내역 우측 월별 합계 확인 → 채널별 충전 vs 소진 일치 여부
2. 30일 ROAS = 1.5x 미만이면 채널 재배분 검토
3. 광고운영 KPI 목표 vs 실적 비교 (📚 참조 시트의 목표_벤치)

---

## 트러블슈팅

### 통합대시보드 표가 깨졌어
1. **채널 매트릭스(행 17~23) 깨짐**
   - 함수 셀렉터 → `updateChannelMatrixWithGA4` 실행 → 자동 복구
2. **핵심 KPI 상세(행 9~14) 깨짐**
   - `updateKPISummary` 실행
3. **SNS 보고표(행 28~33) 깨짐**
   - `updateSNSReport` 실행
4. **네비게이션(행 25~27) 사라짐**
   - `restoreDashboardNav` 실행
5. **전부 깨짐**
   - 메뉴 → `⚡ 전체 새로고침` (위 함수들 한번에 실행)

### GA4 데이터가 안 들어와
- GA4_자동 시트 마지막 행 날짜 확인
- 매일 새벽 1시 트리거가 fetchGA4Daily 실행 (Asia/Seoul)
- 안 들어오면:
  1. Apps Script → 트리거 메뉴 → `fetchGA4Daily` 트리거 활성 확인
  2. 수동 실행: `🛠 폰스팟 운영` → `🔄 GA4 최신 데이터 가져오기`
  3. 30일 전체 다시 받기: `📥 GA4 30일 다시 가져오기`

### 출처미상 % 가 너무 높아 (>30%)
- 원인: 문의 들어왔는데 D열 유입채널 입력 안 됨
- 해결: 카톡/전화 문의 응답 시 첫 메시지로 "어디 광고 보고 오셨어요?" 묻고 즉시 D열 입력

### 매트릭스에서 메타 카톡클릭이 너무 적게 잡혀
- GA4 attribution 손실 (세션 타임아웃, referral 변환 등)
- 이미 적용된 개선: 세션 타임아웃 2시간, 메타 referral 제외
- 전체 카톡클릭(행 23) 과 채널 매트릭스 메타 행을 비교해서 (not set) 비율 확인

### 시티마켓 데이터 추적
- 시티마켓 GTM(GTM-TMXR6VL9)에 폰스팟 GA4 G-2K74Y3FY65 dual-tracking 됨
- cross-domain 측정 활성 (litt.ly + citymarket.co.kr)
- GA4_자동 시트에서 hostname=citymarket.co.kr 데이터 확인

---

## 신규 광고 시작 시 체크리스트

1. **랜딩 URL 결정** — 기본: `https://litt.ly/phonespot`
2. **UTM 생성** — UTM_생성기 시트 노란 셀 입력 → 생성된 URL 복사
   - utm_source: meta / google / naver / kakao / daangn 등
   - utm_medium: cpc / social / display / video / post 등
   - utm_campaign: 영문 소문자+숫자+언더바 (예: `s26_promo`, `daangn_sa`)
   - utm_content: A/B 소재 구분 (선택)
3. **광고 플랫폼에 UTM URL 등록**
4. **해당 채널 시트에 첫 행 입력** (날짜만이라도)
5. **2~3일 후 GA4_자동에서 source/medium 정상 인식되는지 확인**

---

## 절대 하지 말 것

- ❌ 결제 시점에 유입채널을 추측해서 입력 (확실 모르면 `불확실`로 표기)
- ❌ Apps Script에서 옛 함수 실행: `rebuildDashboard`, `polishDashboardUI`, `masterCleanup` 등 (시트 구조 망가짐)
- ❌ 통합대시보드 셀 수동 편집 (수식 깨짐. 함수로만 재생성)
- ❌ 시크릿/토큰을 시트나 ads/ 폴더에 직접 저장 (반드시 `_secrets/`로)

---

## 인계 시 필요한 것

새 운영자에게 넘길 때:
1. 이 매뉴얼 (`ads/MANUAL.md`)
2. Apps Script 코드 백업 (`ads/code/apps_script/Code.gs`)
3. 시트 구조 문서 (`ads/data/sheet_structure.md`)
4. 키 자산 reference (`ads/README_FOR_AI.md`)
5. Google Sheets / GA4 / Google Ads 권한 이전 (313jongmin@gmail.com 개인 계정 → 회사 계정)

---

작성: 2026-05-30
최종 수정: 2026-05-30
