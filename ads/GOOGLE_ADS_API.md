# 구글 Ads API 자동수집 — 운영 가이드 (2026-06-19 신설)

> 메타·네이버처럼 노출/클릭/지출을 API로 자동 수집. **현재 Google 토큰 승인 대기 중** → 승인 오면 STEP 4부터 재개.

## 0. 현재 상태 (2026-06-19)
- **코드·계정연동 완성. 막힌 건 개발자 토큰 등급 하나.**
- 신규 개발자 토큰 = **Test 등급** → 실제(운영) 계정 못 읽음. **Basic 액세스 승인 필요.**
- **2026-06-19 Basic 액세스 신청 제출 완료** (보통 ~3영업일, 더 걸릴 수도). 승인 메일 = API 센터 연락 이메일(313jongmin@gmail.com)로 옴.
- 설계 문서 PDF 첨부 제출: `ads/PhoneSpot_GoogleAdsAPI_DesignDoc.pdf`.
- 승인 전까지는 **수기 입력 경로 유효** (구글_통합 D/E/F 직접 입력 → GA4 매칭 G~P는 자동).

## 1. 파일
- `apps_script/google-ads-sync.js` — Ads API 수집 (refresh_token→access_token→searchStream GAQL v23, ad_group 단위 → 구글_통합 D/E/F upsert → syncGoogleGA4 후속).
- `apps_script/google-sync.js` — GA4 매칭(G~P) + 🔵 구글 메뉴 정의.
- API 버전 바꿀 때 = `GADS_API_VERSION` 상수만. (v19는 2026-02 종료, 현재 v23)

## 2. Script Property 6개 (Apps Script 프로젝트 설정 → 스크립트 속성)
GOOGLE_ADS_DEVELOPER_TOKEN / CLIENT_ID / CLIENT_SECRET / REFRESH_TOKEN / LOGIN_CUSTOMER_ID / CUSTOMER_ID
- LOGIN_CUSTOMER_ID = 관리자(MCC) = **3964705146** (신청서 MCC = 396-470-5146).
- CUSTOMER_ID = 실제 광고 집행 계정.
- 코드가 하이픈 자동 제거. LOGIN 비우면 login-customer-id 헤더 자동 생략.

## 3. ★ 함정 — MCC/CUSTOMER 반대 저장 주의 (2026-06-19 종민 메모)
- 테스트 중 LOGIN/CUSTOMER 값을 **반대로 저장한 적 있음.** 승인 후 재개 시 반드시 재확인.
- 확정 사실: 진단(listAccessibleCustomers) 결과 313jongmin이 **두 계정 다 직접 접근 가능**
  (3964705146, 1409738298 둘 다 목록에 있었음).
- 신청서 기준 **MCC = 3964705146**. 따라서 광고 집행 계정(CUSTOMER) = 나머지 번호(1409738298)일 가능성 큼 — 단 승인 후 실제 데이터로 검증할 것.
- **확정 사실 2**: login-customer-id에 MCC를 넣으면 USER_PERMISSION_DENIED 발생(MCC가 그 계정 미관리). **login-customer-id를 비우면(직접접근) 통과**했고, 그 다음 단계 에러가 DEVELOPER_TOKEN_NOT_APPROVED였음 = 권한경로는 LOGIN 비우는 쪽이 정답.

## 4. 승인 오면 재개 절차
1. API 센터에서 액세스 등급 = Basic 확인.
2. Script Property 점검: CUSTOMER_ID = 광고 집행 계정 번호 맞는지. **LOGIN_CUSTOMER_ID는 일단 비워두고 시작**(직접접근).
3. 시트 🔵 구글 → **🔎 접근가능 계정 목록(진단)** → MCC/CUSTOMER 번호 확인.
4. 🔵 구글 → **🔑 Ads 연결 테스트**.
   - 성공(계정명/통화 뜸) → 5번.
   - USER_PERMISSION_DENIED → CUSTOMER_ID를 다른 직접접근 번호로 교체 후 재시도.
5. **📥 Ads API 백필 (최근 30일)** → D~F 채워짐 + GA4 매칭.
6. 정상 → **⏰ Ads 수집 Trigger 설정 (02:25)**.

## 5. 메뉴 (🔵 구글)
📥 Ads API 수집(7일) / 📥 백필(30일) / 🔑 연결테스트 / 🔎 접근가능 계정 진단 / 🔄 GA4 매칭 / 🆕 시트신설 / 🔍 미매핑 / ⏰ GA4 Trigger(02:35) / ⏰ Ads Trigger(02:25)

## 0-1. 신청 반려/재제출 이력 (2026-06-22)
- 1차 반려: "website http://phonespot.co.kr has no content related to application" — 사이트가 JS렌더라 크롤러가 빈 셸로 봄. (폼에 phonespt.co.kr=죽은 도메인 적었을 가능성도.)
- 대응 = Google이 허용한 "상세 사업모델+용도 설명+목업" 경로. 재제출 변경점:
  · Q5 = https://www.phonespot.co.kr (o 있음, 실사이트)
  · Q6 = 상세 사업모델 텍스트(매장 소매+멀티채널 광고+카톡/전화 전환, 읽기전용 리포팅)
  · Q7 = ads/PhoneSpot_GoogleAdsAPI_DesignDoc_v2.pdf (사업모델+용도+대시보드 목업 포함)
- 주의: 같은 응답 재제출 금지(반려메일). 위처럼 응답을 바꿔야 함. 추가로 통합대시보드 실제 스크린샷 첨부하면 성공률↑.
