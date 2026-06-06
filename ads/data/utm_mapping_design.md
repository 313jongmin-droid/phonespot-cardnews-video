# UTM_매핑 시트 설계

> 메타 캠페인명 (한국어 자유) ↔ utm_campaign (영문 슬러그) 매핑. GA4 정확 매칭의 정답지.
> 작성: 2026-06-05

---

## 컬럼 구조

| 컬럼 | 헤더 | 입력 방식 | 예시 | 비고 |
|------|------|---------|------|------|
| A | utm_campaign | 수기 | `bom_sale_s25` | UTM 생성기에서 박은 값. 영문 소문자+숫자+언더바 |
| B | utm_medium | 수기 (드롭다운) | `display` | cpc/display/social/video/post/profile/bio/message/referral/qr/community |
| C | utm_source | 수기 (드롭다운) | `meta` | meta/google/naver/kakao/daangn/threads/tiktok/instagram/youtube/blog/citymarket/ppomppu/offline |
| D | 메타 캠페인ID | 자동 | `120225...` | autoFillMetaCampaignsIntoMapping 함수가 메타 API에서 가져옴 |
| E | 메타 캠페인명 | 자동 | `S26 봄세일 5/30 시작` | 메타 광고관리자 한국어 그대로 |
| F | 광고세트 | 자동/수기 | `핵심타겟 만 25~45` | 캠페인 1개에 광고세트 여러 개 가능 |
| G | 광고소재 PS_ID | 수기 | `PS-007` | 메타_소재 시트에서 확인 |
| H | 시작일 | 수기 | `2026-05-30` | |
| I | 종료일 | 수기 | `(빈 칸)` | 비어있으면 진행중 |
| J | 메모 | 수기 | `손실회피 카피` | 자유 |
| K | GA4 매칭상태 | 자동 (수식) | `🟢 매칭` | A열 utm_campaign이 GA4_자동에 있는지 검사 |

---

## K열 자동 수식

```
=IF(A2="","",IFERROR(IF(COUNTIFS('GA4_자동'!D:D,A2,'GA4_자동'!B:B,C2)>0,"🟢 매칭","🔴 미매칭"),"-"))
```

- A열 비어있으면 빈 칸
- GA4_자동 시트의 D열 (sessionCampaignName) = A열 (utm_campaign) + B열 (sessionSource) = C열 (utm_source) 일치하는 행이 있으면 🟢
- 없으면 🔴 (UTM 박은 광고가 아직 클릭 안 됐거나 UTM 표기 오타)

---

## 데이터 검증 (드롭다운)

### B열 utm_medium
```
cpc / display / social / video / post / profile / bio / message / referral / qr / community
```

### C열 utm_source
```
meta / google / naver / kakao / daangn / threads / tiktok / instagram / youtube / blog / citymarket / ppomppu / offline
```

→ 두 컬럼 모두 데이터 검증 드롭다운 자동 셋업 (setupUtmMappingSheet 함수)

---

## 메타_통합 시트 연동

메타_통합 시트의 D열 (utm_campaign) 자동 수식:

```
=IFERROR(IF(B2="","",VLOOKUP(B2,UTM_매핑!D:A,-3,FALSE)),"")
```

- B2 = 메타 캠페인ID
- VLOOKUP 으로 UTM_매핑 시트 D열에서 찾아 A열 utm_campaign 가져옴
- 못 찾으면 빈 문자열

→ 메타_통합 시트 GA4 매핑 수식 (I~L) 이 C열 (캠페인명) 대신 D열 (utm_campaign) 참조

---

## 새 광고 만들 때 흐름

```
1. UTM_생성기 시트에서 URL 생성
   · utm_source = meta
   · utm_medium = display
   · utm_campaign = bom_sale_s25
   · utm_content = image_1 (선택)
   → 생성된 URL 복사

2. 메타 광고관리자에서 광고 등록
   · 캠페인명 = "S26 봄세일 5/30 시작" (한국어 OK)
   · URL 매개변수 = 위 UTM URL

3. UTM_매핑 시트 한 행 추가
   · A = bom_sale_s25
   · B = display
   · C = meta
   · D, E (자동으로 채워질 예정 — 다음 sync 시)
   · G = PS-007 (이 광고에 사용한 소재 ID)
   · H = 2026-05-30 (시작일)
   · J = 메모

4. 메뉴 → 🔁 메타 캠페인 → 매핑 시트 자동 추가
   → D (캠페인ID), E (캠페인명) 자동 채워짐
   
5. 다음날 새벽 1:30 syncAll 자동 실행
   → 메타_통합 시트에 어제 데이터 자동
   → D열 utm_campaign 자동 매칭
   → I~N (GA4) 정확 매핑

6. UTM_매핑 시트 K열 (매칭상태) 🟢 확인
```

---

## 기존 광고 일괄 매핑 (셋업 시 1회)

1. 메뉴 → 🗂 UTM_매핑 시트 셋업 — 새 시트 생성
2. 메뉴 → 🔁 메타 캠페인 → 매핑 시트 자동 추가 — 활성 캠페인 D~F 자동
3. A~C/G/H 수기 입력 (utm_campaign 값은 메타 광고관리자에서 광고 URL 보고 확인)
4. 메뉴 → 🔧 메타_통합 utm_campaign 컬럼 추가 (1회) — 기존 메타_통합 시트에 D열 삽입 + 수식 갱신
5. 메뉴 → ⏪ 30일 백필 — 메타_통합 시트 30일 데이터 자동

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| K열 모두 🔴 미매칭 | utm_campaign 박힌 광고 아직 클릭 X 또는 UTM 표기 오타 | GA4_자동 시트 D열 확인 |
| D열 비어있음 (메타_통합) | UTM_매핑 시트에 그 캠페인 행 없음 | autoFillMetaCampaignsIntoMapping 실행 |
| VLOOKUP 에러 | UTM_매핑 시트 이름 오타 | 시트명 정확히 "UTM_매핑" |
| 같은 utm_campaign 여러 메타 캠페인에 박힘 | UTM 표기 중복 | A열 정렬 + 중복 체크 |

---

## 표준 UTM 표기 (UTM 생성기 시트 참조)

| 우리 채널 | utm_source | utm_medium | 캠페인 예시 |
|---------|-----------|----------|-----------|
| 메타 인스타 광고 | meta | social | s26_promo |
| 메타 페북 광고 | meta | social | fb_s26_pre |
| 당근 광고 | daangn | social | gz_local |
| 카카오 모먼트 | kakao | social | kk_banner |
| 카카오톡 플친 메시지 | kakao | message | kk_msg_apr |
| 네이버 검색광고 | naver | cpc | s26_search |
| 네이버 디스플레이 | naver | display | gdn_retarget |
| 구글 검색광고 | google | cpc | gsearch_s26 |
| 구글 디스플레이 | google | display | gdn_brand |
| 유튜브 광고 | google | video | yt_s26 |
| 스레드 organic | threads | post | th_daily |
| 인스타 organic | instagram | post | ig_reel_05 |
| 틱톡 organic | tiktok | post | tt_daily |
| 유튜브 organic | youtube | post | yt_review |
| 네이버 블로그 | blog | post | nblog_review |
| 네이버 카페 | naver | community | nc_phonespot |
| 뽐뿌 핫딜 | ppomppu | community | ppm_hotdeal |
| 시티마켓 | citymarket | referral | cm_pb |
| 오프라인 매장 QR | offline | qr | store_qr |
| 명함 QR | offline | qr | card_qr |
| 엘리베이터 광고 QR | offline | qr | elevator_qr |

→ utm_campaign은 영문 소문자+숫자+언더바. 한글/공백 금지.

---

작성: 2026-06-05
