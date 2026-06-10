# 인스타 시트 자동화 — 보류 (2026-06-10 작성)

> **상태: 메타 잠금 안정화 며칠 후 진행.** 인증 직후 권한 변경 시 의심 트리거 가능.

---

## 한 줄 요약

Instagram Graph API (메타 산하) 활용해서 인스타 게시물별 조회수/좋아요/리치 + 일별 팔로워를 인스타 시트에 자동 입력. 사용자 매일 수기 입력 → 0분으로 단축.

---

## 사전 조건

### 인스타 계정
- **Business** 또는 **Creator** 계정만 (Personal ❌)
- 페이스북 페이지에 연동돼있어야 함

### 메타 토큰 권한 추가 (System User Token 그대로 사용)
현재 META_TOKEN scopes:
- ✅ ads_management, ads_read, business_management, pages_read_engagement, public_profile

**필요 추가**:
- ❌ `instagram_basic`
- ❌ `instagram_manage_insights`

→ 비즈니스 매니저 → 시스템 사용자 `phonespot-sync` → 권한 편집 + 인스타 비즈니스 계정 자산 추가. **새 토큰 발급 X, 기존 토큰에 자동 반영.**

### PropertiesService 추가
- `INSTAGRAM_BUSINESS_ID` = `17841xxxxxx` (인스타 비즈니스 계정 ID, 페이스북 페이지 설정에서 확인)
- META_TOKEN 그대로 사용

---

## 가져올 데이터 (자동)

### 게시물별
- id, caption (1줄 발췌), media_type, permalink, timestamp
- impressions (노출), reach (도달), video_views (영상 조회)
- likes, comments, saved (저장), shares
- engagement_rate

### 계정별
- follower_count (현재)
- 일별 follower_count 추이 (30일 한도)
- 새 팔로우, 언팔로우 (가능 시)

---

## 인스타 시트 컬럼 매핑 (예상)

| 컬럼 | 자동/수동 | 데이터 출처 |
|---|---|---|
| A 날짜 | 자동 | post timestamp → YYYY-MM-DD |
| B 형식? | 자동 | media_type (IMAGE / VIDEO / REELS / CAROUSEL) |
| C 주제 | 자동 | caption 1줄 발췌 (80자) |
| D 링크 | 자동 | permalink |
| E 조회수 | 자동 | video_views (영상) or impressions (이미지) |
| F 좋아요 | 자동 | likes |
| G 팔로워 | 자동 | 그날 계정 follower_count |
| H 운영메모 | 수동 | 사용자 입력 |
| I 비고 | 수동 | 사용자 입력 |

**(실제 시트 구조 확인 후 컬럼 맞춤)**

---

## 제약사항

| 항목 | 제약 |
|---|---|
| 인사이트 30일 한도 | 일부 메트릭 30일까지만 (Reels는 더 길게 가능) |
| Rate limit | 시간당 200 호출 (게시물 많아도 충분) |
| Personal 계정 | API 접근 불가. Business/Creator 전환 필요 |
| 캡션 한글 | URL 인코딩 주의 |

---

## 코드 구상 (`meta-sync.gs` 추가)

```javascript
// ============ 인스타 시트 자동화 ============
const INSTAGRAM_BUSINESS_ID_KEY = 'INSTAGRAM_BUSINESS_ID';
const SHEET_INSTAGRAM = '인스타';

function getInstagramId() {
  const id = PropertiesService.getScriptProperties().getProperty(INSTAGRAM_BUSINESS_ID_KEY);
  if (!id) throw new Error('INSTAGRAM_BUSINESS_ID 없음');
  return id;
}

function syncInstagramDaily() {
  const igId = getInstagramId();

  // 1. 게시물 리스트 (최근 30개)
  const mediaRes = metaFetch(`/${igId}/media`, {
    fields: 'id,caption,media_type,permalink,timestamp,thumbnail_url',
    limit: 30
  });

  // 2. 각 게시물별 인사이트
  const ss = SpreadsheetApp.getActive();
  const sheet = ss.getSheetByName(SHEET_INSTAGRAM);
  if (!sheet) throw new Error('인스타 시트 없음');

  // ... (게시물별 insights 호출, 시트 매칭 update/append, dedup)
}
```

---

## 진행 순서 (며칠 후)

1. ⏳ **대기**: 메타 잠금 안정화 (3-7일)
2. ✅ **권한 추가**: 비즈니스 매니저 → 시스템 사용자 → 인스타 권한 + 자산
3. ✅ **토큰 디버거 확인**: scopes에 instagram_* 추가됐는지
4. ✅ **PropertiesService 추가**: INSTAGRAM_BUSINESS_ID
5. ✅ **인스타 시트 정확한 컬럼 구조 확인** (Claude에게 시트 1줄 보여주기)
6. ✅ **syncInstagramDaily 코드 박기** + 테스트
7. ✅ **syncAll에 통합** + 트리거 (또는 별도 시간 03:00)

---

## 다른 SNS (참고)

| SNS | API | 자동화 가능성 |
|---|---|---|
| **인스타** | Instagram Graph API (메타) | ✅ 본 문서 |
| **유튜브** | YouTube Data + Analytics API | ✅ 이미 구현 (`youtube_sync.gs`) |
| 스레드 | Threads API (메타) | ⚠️ 베타. 일부 가능 |
| 틱톡 | TikTok Business API | ⚠️ 별도 앱 등록 필요. 복잡 |

→ 인스타 다음 우선순위: 틱톡 (별도 검토)

---

작성: 2026-06-10 (메타 광고 자동화 1차 완성 직후)
