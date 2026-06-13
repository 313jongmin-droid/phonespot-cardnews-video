# 네이버 검색광고 자동화 — ✅ 완료 (2026-06-11)

> **메타_통합 패턴 그대로 복제** + 별도 시트/메뉴/트리거. 광고그룹 단위 통합.

---

## 한 줄 요약

네이버 검색광고 API → 광고그룹별 통계 + UTM 매핑 + GA4 매칭 자동 수집. 매일 02:15 자동.

---

## 사전 조건

### API 인증 (PropertiesService 등록)
- `NAVER_API_LICENSE` (Access License)
- `NAVER_SECRET_KEY` (비밀 키 — 절대 코드/공유 X)
- `NAVER_CUSTOMER_ID` = `1559128` (광고주 ID, ads.naver.com URL)

### API 발급 위치
- ads.naver.com (네이버 광고 신규 UI) 또는 searchad.naver.com → 도구 → API 사용자 관리 → API 라이선스 등록
- 라이선스 키 + 비밀 키 발급 (1회만)

---

## 코드 구조

**파일**: `naver-sync.gs` (메타와 완전 분리)

| 함수 | 역할 |
|---|---|
| `syncNaverIntegrated(targetDate?)` | 메인. 광고그룹별 일자 통계 → 네이버_통합 시트 |
| `naverFetch_(method, uri, params)` | HMAC-SHA256 시그니처 인증 호출 |
| `ensureNaverUtmMappingSheet_()` | 네이버_UTM_매핑 시트 자동 생성 |
| `autoDiscoverNaverAdgroups_(rows, ymd)` | 새 광고그룹 발견 시 UTM_매핑에 자동 추가 |
| `backfillNaverIntegrated30Days()` | 30일 백필 (수동) |
| `showUnmappedNaverAdgroups()` | 미매핑 광고그룹 목록 alert |
| `listAllAdgroups()` | 캠페인+광고그룹 디버그 출력 |
| `testNaverConnection()` | 연결 테스트 |
| `buildNaverSyncMenu_(ui)` | 🔍 네이버 자동화 메뉴 (별도) |
| `setupNaverTriggers()` | 매일 02:15 트리거 등록 (별도) |

---

## API 정확한 호출 방식 (2026-06-11 실증)

### `/stats` 광고그룹별 통계 — **결정적**

```javascript
naverFetch_('GET', '/stats', {
  ids: adgroupIds.join(','),                      // ★ 콤마 구분 문자열 (JSON 배열 ❌)
  fields: JSON.stringify(['impCnt', 'clkCnt', 'salesAmt']),
  timeRange: JSON.stringify({ since: ymd, until: ymd })
  // ★ statType 미지정 (ADGROUP / AD / AD_DETAIL 등 다 ❌)
});
```

### 응답 구조
```json
{
  "data": [
    {"id": "grp-...", "impCnt": 13, "clkCnt": 1, "salesAmt": 128},
    ...
  ],
  "compTm": "...",
  "cycleBaseTm": "..."
}
```

### HMAC-SHA256 인증
```
message = timestamp + "." + method + "." + uri
signature = base64(HMAC-SHA256(SECRET_KEY, message))
headers:
  X-Timestamp:  timestamp (ms)
  X-API-KEY:    API_LICENSE
  X-Customer:   CUSTOMER_ID
  X-Signature:  signature
```

### URL Base
- `https://api.searchad.naver.com`

---

## 신설 시트

### 네이버_통합 (19컬럼, 메타_통합 동일 구조)
```
A 날짜 / B 캠페인ID / C 캠페인명 / D 광고그룹ID / E 광고그룹명 /
F 노출 / G 클릭 / H 지출 / I CTR(수식) / J CPC(수식) /
K GA4세션 / L 카톡클릭 / M 전화클릭 / N 시티마켓 / O 카톡전환률 / P 카톡당CPC /
Q 문의수 / R 개통수 / S 메모
```

### 네이버_UTM_매핑 (별도, 메타와 분리)
```
A 네이버 광고그룹명(한글) / B utm_campaign(영문) / C 첫 발견일 / D 상태 / E 메모
```
- A열: 자동 발견 (덮어쓰지 X)
- B열: 사용자 수동 입력 (GA4 utm_campaign 영문 슬러그)
- D열: ⚠️ 매핑 필요 / ✅ 매핑됨 자동 토글

---

## GA4 매칭 수식 (네이버_통합 K~P열)

```
utmSlug = IFERROR(VLOOKUP(광고그룹명, 네이버_UTM_매핑!A:B, 2, FALSE), 광고그룹명)
ga4Base = source=naver + 날짜(yyyymmdd) + utm_campaign=utmSlug

GA4세션  = SUMIFS(G:G, ga4Base, eventName="session_start")
카톡클릭 = SUMIFS(F:F, ga4Base, eventName="kakao_chat_click")
전화클릭 = SUMIFS(F:F, ga4Base, eventName="phone_click")
시티마켓 = SUMIFS(F:F, ga4Base, eventName="citymarket_click")
```

UTM_매핑 시트의 B열 슬러그 채워야 GA4 매칭됨. 비어있으면 한글 광고그룹명으로 직접 매칭 시도 (보통 매칭 0).

---

## KT 필터 (자동 제외)

캠페인명에 **'KT' 또는 '다이렉트샵'** 포함 시 자동 제외:
```javascript
const NAVER_KT_FILTER = ['KT', '다이렉트샵'];
```

→ KT 캠페인 추가돼도 자동 분리. `ads_kt/` 별도 시트로 관리 시 자체 동기화 코드 필요.

---

## 메뉴 (🔍 네이버 자동화 — 별도)

- 📊 광고그룹별 통합 (어제)
- ⏪ 30일 백필
- 🔍 미매핑 광고그룹 보기
- 🔑 연결 테스트
- 📋 캠페인+그룹 목록 보기
- ⏰ 네이버 Daily Trigger 설정

---

## 트리거 (별도)

`setupNaverTriggers()`:
- 매일 02:15 `syncNaverIntegrated` (메타 02:00 / 메타인사이트 01:45 다음 순서)

deleteTrigger 조건에 `syncNaverIntegrated` / `syncNaverDaily` 둘 다 포함 (구버전 정리용).

---

## 디버깅 메모 (2026-06-11 해결)

### 문제 1 — `statType=ADGROUP`이 400 거부
- 네이버 `/stats`는 ADGROUP / AD / AD_DETAIL / KEYWORD 등 다 거부
- **해결**: statType 파라미터 자체를 빼면 광고그룹 ID로 자동 인식

### 문제 2 — `ids: JSON.stringify(배열)` 형식 거부
- 응답: `"유효하지 않은 ID 형식입니다"`
- **해결**: `ids: adgroupIds.join(',')` 콤마 구분 문자열

### 문제 3 — 30일 백필 "성공 29일" 떴는데 시트 없음
- 매번 `rows.length === 0`이라 시트 생성 로직 안 탐
- catch 안 던지니 success로 카운트됨
- **위 2개 수정 후 정상 작동**

---

## 향후 확장

### 다른 캠페인 타입 (POWER_CONTENTS / PLACE)
- 캠페인 6개 중 [5] 파워컨텐츠_블로그 (POWER_CONTENTS), [6] 폰스팟_플레이스광고 (PLACE) 포함
- `/stats` 통합 호출되므로 별도 처리 불필요 (이미 다 잡힘)

### 키워드 단위 확장 (선택)
- 현재 광고그룹 단위. 키워드 단위 필요 시 `/ncc/keywords?nccAdgroupId=...` + `/stats` (statType 미지정)
- 광고그룹 31개 × 키워드 10~50개 = API 호출 폭주. 필요 시점에 검토

---

작성: 2026-06-11
