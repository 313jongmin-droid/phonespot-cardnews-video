# SNS 자동화 가능성 매트릭스 (2026-06-11)

> 메타 광고 자동화(`meta-sync.gs`) + 유튜브 자동화(`youtube_sync.gs`) 패턴을 다른 채널에 확장 가능한지 정리. **팩트 기반** — 추측 ❌, 공식 API 유무·인증 복잡도·수집 가능 데이터만 명시.

---

## 📊 매트릭스 — SNS 운영 채널 (콘텐츠/포스트 자동수집)

| 채널 | 자동화 가능 | API | 필요 권한/인증 | 수집 가능 데이터 | 복잡도 | 상태 |
|---|---|---|---|---|---|---|
| **유튜브** | ✅ 완료 | YouTube Data API + Analytics API | OAuth (구글 계정) | 영상별 조회/좋아요/retention, 일별 구독자 | 중 | `youtube_sync.gs` (매일 03:30) |
| **인스타** | ✅ 완료 | Instagram Graph API (메타 산하) | META_TOKEN에 `instagram_basic` + `instagram_manage_insights` 권한 포함 | 게시물별 조회수/좋아요/permalink, 일별 팔로워 | 하 | `meta-sync.gs` 내 `syncInstagramDaily` (매일 02:00) |
| **스레드** | ⚠️ 가능 | Threads API (메타 산하, 2024-06 공개) | 기존 META_TOKEN에 `threads_basic` + `threads_manage_insights` 권한 추가 | 포스트별 조회수/좋아요/답글/공유, 본인 계정만 | 하~중 | 인스타 이후 |
| **틱톡** | ⚠️ 가능 | TikTok Display API + Business API | 별도 앱 등록 (메타 토큰과 별개) + OAuth 2.0 | 비디오별 조회/좋아요/댓글/공유, 일부 통계는 비즈니스 계정만 | 상 | 미정 |
| **네이버 블로그** | ❌ 불가 | 공식 API 없음 | — | — | — | 수기 입력 유지 |
| **네이버 플레이스** | ⚠️ 부분 가능 | 네이버 비즈니스 API (제한적) | 네이버 비즈니스 인증 | 일부 통계만, 키워드 순위 ❌ | 중 | 후순위 |
| **네이버 카페** | ❌ 불가 | 공식 API 없음 | — | — | — | 수기 입력 유지 |

## 📊 매트릭스 — 광고 채널 (광고비/소재/성과 자동수집)

| 채널 | 자동화 가능 | API | 인증 | 상태 |
|---|---|---|---|---|
| **메타 광고** | ✅ 완료 | Meta Marketing API v22.0 | System User Token | `meta-sync.gs` (매일 01:30) |
| **구글 광고** | ✅ 가능 | Google Ads API | OAuth + Developer Token (승인 필요) | 미정 (6/5 잠정 종료) |
| **카카오 모먼트** | ⚠️ 가능 | 카카오 모먼트 API | 카카오 비즈니스 인증 | 미정 |
| **카카오톡 채널** | ❌ 불가 | 통계 API 미공개 | — | 자동수집 불가 확인 (2026-06-11) |
| **네이버 검색광고** | ✅ 완료 | 네이버 검색광고 API (HMAC-SHA256) | API 라이선스 + Secret Key | `naver-sync.gs` 광고그룹 단위 (매일 02:15) |
| **당근 광고** | ❌ 불가 | 공식 API 공개 X (현재) | — | 수기 입력 유지 |

---

## 🎯 권장 우선순위 (난이도 + 효과 종합)

### ✅ 1순위 — 인스타 (완료 2026-06-11)
- 토큰 신규 발급 (인스타 권한 포함) + `INSTAGRAM_BUSINESS_ID = 17841474706647015` PropertiesService 등록
- `syncInstagramDaily()` 코드 박음 + 매일 02:00 트리거 등록
- 인스타 시트 D열(permalink) 매칭 — 신규 append / 기존 E·F·G 갱신
- 정렬: timestamp 오름차순 → 최신이 시트 하단
- 문서: `INSTAGRAM_AUTOMATION_PENDING.md` (완료 처리)

### 2순위 — 스레드 (⚠️ 보류 — 시스템 사용자 토큰 미지원 가능성)
- **2026-06-11 실측**: 메타 비즈매니저 시스템 사용자 `phonespot-sync` 자산 추가 화면에 **"Threads" 또는 "스레드" 옵션 없음**
- **추정**: Threads API는 시스템 사용자 토큰 모델 미지원. 개인 OAuth만 가능할 가능성 (별도 검토 필요)
- **대안**: ① 별도 앱 생성 후 개인 토큰으로 운영 ② 메타가 시스템 사용자 지원 추가할 때까지 대기
- **권한 후보**: `threads_basic`, `threads_manage_insights`

### 3순위 — 틱톡
- **이유**: 데이터 가치 높음 (현재 시트 "틱톡" 탭 사용 중)
- **블로커**: 별도 앱 등록 + OAuth 흐름 (메타와 분리)
- **복잡도**: 상. 메타 안정화 + 인스타·스레드 완성 후 검토

### 후순위 — 네이버 플레이스 / 카카오톡 채널
- 부분 가능하나 데이터 가치 대비 인증 비용 큼

### 자동화 불가 (수기 유지)
- 네이버 블로그·카페 (공식 API 없음)
- 당근 광고 (공식 API 공개 X)

---

## 🔄 메타 자동화 패턴 (참고)

`meta-sync.gs` 가 가능한 이유:
1. **System User Token** — 만료 없음, 매월 갱신 불필요
2. **시트 직접 update** — Apps Script에서 SpreadsheetApp 사용
3. **Drive MD 저장** — Gemini 분석 결과를 cardnews/shorts task가 Read

다른 SNS도 같은 패턴 적용:
- Apps Script에서 fetch → 시트 update → 인사이트 MD → Drive 저장
- 매일 새벽 트리거로 `setupTriggers()` 안에 함수 추가

---

## ⚠️ 운영 주의사항 (2026-06-11 사고 기반)

`generateMetaInsightsMarkdown` 함수 누락 사고:
- 원인: `meta-sync.gs` 전체 코드 통째 교체 시 패치 함수가 사라짐
- 복구: `meta_insights_patch.js` 통째 박기 + `setupTriggers` 재등록
- **신규 채널 자동화 추가 시에도 동일 위험**. 함수 단위로 박을 것. 코드 통째 교체 ❌

---

## 📌 GA4 자동수집 — 확정

`fetchGA4Daily` 는 `syncAll` (매일 01:30) 안에서 자동 호출. 별도 트리거 등록 불필요.
- 06-11 01:34:57 ✅ 성공 확인 (동기화_로그)
- GA4 데이터는 syncAll → meta_sync → integrated 매칭까지 순차 진행

---

작성: 2026-06-11
