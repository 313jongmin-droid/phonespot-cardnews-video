# PPL_YOUTUBE_OUTREACH_GUIDE — 유튜브 협찬 대상 발굴 + 제안 메일 초안

> **신규 트랙 (2026-06-18 설계, 종민 결정).** 기존 "SNS 크롤링"(경쟁사 광고 벤치마크, `_docs/APIFY_INTEGRATION_GUIDE.md`)과 **별개**.
> **범위(1-b):** 조건 맞는 유튜브 채널 발굴 → 시트 정리 → 채널별 협찬 제안 메일 **초안 자동 작성**. **발송은 수동**(유튜브 정책상 자동 DM 금지).
> **비용:** 시작 단계 **$0** (YouTube Data API v3 무료 쿼터). 유일한 비용 = 나중에 연락처용 Apify 붙일 때(3-b).

---

## 1. 도구 (발굴 소스)

| 경로 | 무엇 | 키/셋업 | 언제 |
|---|---|---|---|
| **A. Apps Script Advanced YouTube Service** | `YouTube.Search.list` + `YouTube.Channels.list` 공개 검색 | 서비스 "YouTube Data API" 추가만(OAuth 쿼터, **새 키 불필요**) | 시트 상주 운영(정본) |
| **B. YouTube Data MCP** (이 세션 연결됨) | `search_videos` / `get_channel_details` / `get_channel_statistics` / `get_channel_top_videos` | 없음 | 즉시 프로토타입·1회 발굴 |
| C. Apify youtube-scraper | About 페이지 링크·이메일 일부 | APIFY_TOKEN, **유료** | 3-b 업글(연락처 보강) 시에만 |

⚠️ 기존 `youtube_sync.js`/`ads/integrations/youtube`는 **본인 채널 분석(OAuth mine:true)** 전용 → 타 채널 발굴엔 못 씀. Search.list는 별도.
⚠️ **채널 이메일은 Data API에 필드 없음.** 3-a 단계 = 채널 **설명(description)** 텍스트에서 이메일 정규식 파싱만(수집률 낮음). 완전 수집은 3-b(Apify) 필요.

---

## 2. 발굴 로직

1. **검색어(주제 키워드)** — 휴대폰 리뷰 / 자급제 / 통신비 절약 / 요금제 / 개통 / 알뜰폰 / 성지 / 갤럭시·아이폰 리뷰 등. `regionCode='KR'`, `relevanceLanguage='ko'`.
2. `Search.list(type='channel' 또는 'video' → channelId 수집)` → 중복 제거 → `Channels.list(part='snippet,statistics')`로 구독자·총조회수·영상수·설명.
3. **규모 필터 (★선택 가능, 프리셋):**
   - 마이크로 `10,000 ≤ subs < 100,000`
   - 중형 `100,000 ≤ subs < 500,000`
   - 무관 (필터 없음, 주제 적합도만)
   - → min/maxSubscribers 파라미터로 구현, 운영자가 셀렉트.
4. **적합도 점수(0~10):** 주제 키워드 매칭(제목·설명) + 활성도(최근 업로드 ≤30일 +2 / ≤60일 +1) + 참여도(평균조회수/구독자 비율) + 한국 채널 여부. 등급 = ★★★(≥7)/★★(4~6)/★(1~3).
5. **이메일 파싱:** 설명란 정규식 `[\w.+-]+@[\w-]+\.[\w.-]+`. 없으면 공백(수동 확인 대상).

---

## 3. 시트 `유튜브_협찬발굴`

| 열 | 헤더 | 비고 |
|---|---|---|
| A | 채널ID | UC... |
| B | 채널명 | |
| C | 구독자 | |
| D | 총조회수 | |
| E | 영상수 | |
| F | 평균조회수 | 총조회수/영상수 |
| G | 주제 태그 | 매칭된 키워드 |
| H | 최근 업로드 | 활성도 |
| I | 설명 발췌 | 200자 |
| J | 외부 링크 | snippet/커스텀URL |
| K | 이메일 | 설명란 파싱(3-a) |
| L | 규모대 | 마이크로/중형/대형 |
| M | 적합도 점수 | 0~10 |
| N | 등급 | ★★★/★★/★ |
| O | 제안 메일 초안 | LLM 생성 |
| P | 상태 | 발굴→초안→검토→발송→회신/보류 |
| Q | 발굴일 | |

---

## 4. 제안 메일 초안 (자동 작성)

- **엔진:** Gemini(`GEMINI_API_KEY` 재사용) 또는 Claude. 채널 주제·최근 영상 톤 반영한 **채널별 1문단 개인화** + 공통 템플릿(폰스팟 소개 + 협찬 조건 + CTA).
- **템플릿 골자:** ① 채널 언급(최근 영상/주제 구체적으로) ② 폰스팟 = 지역 휴대폰 성지, 협찬 제안 ③ 조건(제품 협찬/원고료/기간) ④ 회신 유도. **과장·허위 금지**, 폰스팟 실제 조건만.
- **발송:** 시트 O열 초안 검토 → **수동 발송**(이메일). 자동 DM ❌(계정정지 위험).

---

## 5. 구현 단계 (새 task용)

- **L1 (지금):** MCP(경로 B)로 키워드 5~10개 발굴 → 규모/적합도 필터 → 시트 `유튜브_협찬발굴` 채우기 → O열 제안 초안. 즉시 결과.
- **L2:** Apps Script(경로 A)로 상주화 — 메뉴/함수 + 주기 갱신. 발굴 로직·시트·초안 생성 함수 이식.
- **L3 (선택):** Apify(경로 C)로 이메일·About 링크 보강 → K열 채움율↑.

---

## 5-A. L2 구현 정본 (2026-07-13, Apps Script + Apify)

> MCP 경로 B는 공유 프로젝트 **Search 쿼터(하루 100회) 소진**으로 발굴 불가 이슈 발생 → **Apify 경로로 L2 상주화**(종민 결정 2026-07-13). Apify는 쿼터 없음.

- **코드:** `apps_script/ppl_youtube.js` (신설). 메뉴 훅 = `Code.js` onOpen `buildPplYoutubeMenu_` (라인 203 부근).
- **액터:** `streamers/youtube-scraper` (api path `streamers~youtube-scraper`). 단가 **$0.005 / 결과**.
- **토큰:** 기존 `APIFY_TOKEN` 스크립트 속성 재사용 (`getApifyToken_`, meta-sync.js 정의). 신규 등록 불필요.
- **2패스 로직 (검색결과 아이템엔 구독자·설명 없음 → 채널URL 보강 필요):**
  - Pass1 `pplDiscoverChannels_` — `searchQueries=[키워드]`, `maxResults=키워드당 N` → 영상결과 `channelUrl` 유니크 수집.
  - Pass2 `pplEnrichChannels_` — `startUrls=[채널/videos]`, `sortVideosBy=NEWEST`, `maxResults=1` → 아이템에 `numberOfSubscribers/channelDescription/channelLocation/channelTotalVideos/channelTotalViews/channelJoinedDate/date(최신)` 포함.
- **필터/점수:** `pplScoreChannel_` (주제태그+설명매칭≤4, 활성도≤2, 참여도 평균조회수/구독자≤3, 한국채널+1). 규모 프리셋 `PPL_SCALE`(micro 1만~10만 기본 / mid / all).
- **이메일(K열):** `pplParseEmail_` = `channelDescription` 정규식 파싱만(3-a, 수집률 낮음). Apify 채널 About 설명 기반.
- **초안(O열):** `pplGenerateDraft_` = Gemini(`GEMINI_API_KEY` 재사용) 개인화 1문단 + `PPL_OFFER_TEMPLATE`(과장 금지 실제 조건). 키 없으면 폴백 문구.
- **시트:** `pplWriteSheet_` → `유튜브_협찬발굴` 17열(A~Q, §3), A열 채널ID 중복 제거, 등급/헤더 서식.
- **메뉴 (🎯 유튜브 협찬발굴):** 발굴 실행(키워드·규모·건수 프롬프트) / ⚡기본 발굴(마이크로 30건) / ✍️초안만 재생성 / 📂시트 열기.
- **함정:** ① 검색결과 아이템엔 구독자 없음 → Pass2 필수. ② 최신업로드 date는 상대/절대 혼재 → `pplActivityScore_`가 방어적 파싱. ③ 채널ID는 `/channel/UC…`일 때만 UC, 핸들뿐이면 `@handle` 저장. ④ Apps Script 6분 제한 — 초안은 상위 N만 생성.
- **멀티브랜드:** push → GitHub Actions clasp --force → 폰스팟 + KT 양쪽 자동 배포. 시트 메뉴 실행만 양쪽에서.

## 6. 셋업 / 주의

- Apps Script 경로 = 프로젝트 → 서비스 → **YouTube Data API** 추가(Advanced Service). OAuth 쿼터 = 무료 10,000 units/day(search 100 units/회 = 하루 ~100검색). 초과 시 익일 리셋.
- **비용:** Data API $0. Apify는 결과당 과금(3-b 이후만).
- **정책:** 자동 이메일 대량 발송·자동 DM = 스팸/ToS 위반 위험 → 초안까지만 자동, 발송 수동.
- 배포(Apps Script화 시) = `apps_script/` git push → GitHub Actions clasp --force. 콘솔 직접수정 ❌.

---

변경 이력
- 2026-07-13: L2 구현(§5-A). MCP Search 쿼터 소진 → Apify `streamers/youtube-scraper` 2패스로 상주화. `apps_script/ppl_youtube.js` 신설, Code.js onOpen 훅. 종민 결정.
- 2026-06-18: 신설. 범위 1-b(발굴+제안초안, 발송수동), 규모 선택 필터, 3-a(Data API 무료) 시작 → 3-b(Apify) 업글. 종민 결정.
