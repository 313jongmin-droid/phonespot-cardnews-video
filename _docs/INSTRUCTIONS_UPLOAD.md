# PROJECT_INSTRUCTIONS_UPLOAD.md
## 폰스팟 광교점 — SNS 5채널 업로드 자동화 인수인계

> **이 문서를 처음 본 Cowork/Claude 세션을 위한 self-contained 작업 가이드.**
> 카드뉴스 생성(PROJECT_INSTRUCTIONS.md)·숏폼 영상(PROJECT_INSTRUCTIONS_SHORTS.md)과는 **별도 테스크**로 관리한다.
> 이유: OAuth 토큰 5개를 한 폴더에 모으면 유출 시 동시 노출 / 계정 정지 격리 / API 정책 변경 대응 / 권한 신청 시차.

---

## 0. 한 줄 요약

이미 생성된 카드뉴스(`output/<slug>/`) + 숏폼 영상(`output/<slug>/video.mp4`)을 입력으로 받아, **스레드 · 인스타그램 · 유튜브 Shorts · 틱톡 · 네이버 블로그** 5채널에 자동/반자동 게시한다.

---

## 1. 입력 데이터 구조 (변경 금지)

```
C:\Users\di898\Documents\phonespot_cardnews\
├─ articles\<slug>.json                  ← 메타+캡션 원본
├─ output\<slug>\
│  ├─ 1x1\card_1.jpg ~ card_6.jpg        ← 인스타 캐러셀용
│  ├─ 4x5\card_1.jpg ~ card_6.jpg        ← 네이버 블로그용 (세로형)
│  ├─ 9x16\card_1.jpg ~ card_6.jpg       ← 스토리/Shorts 썸네일용
│  ├─ captions.md                         ← 5채널 캡션 (이미 채널별로 섹션 분리됨)
│  └─ video.mp4                           ← 숏폼 (SHORTS 테스크 산출물)
```

> **captions.md 파싱 규칙**
> `## 1. 네이버 블로그` / `## 2. 스레드` / `## 3. 인스타그램` / `## 4. 유튜브` / `## 5. 틱톡` 헤더 기준으로 분리.
> 본문 내 `{LITTLY}` `{PRECON_URL}` 토큰은 `.env`의 `LITTLY` `PRECON_URL` 값으로 치환.

---

## 2. 채널별 자동화 현실 (팩트)

| 채널 | 공식 API | 자동 게시 가능 범위 | 인증 방식 | 일 제한 |
|---|---|---|---|---|
| 스레드 | Meta Threads API (2024.6 공개) | 텍스트+이미지+영상 직접 게시 | OAuth 2.0 (User Access Token) | 250 게시물 |
| 인스타그램 | Instagram Graph API | 카드뉴스 캐러셀 직접 게시 (이미지 6장) | OAuth 2.0 + **비즈니스 계정 + Facebook 페이지 연동 필수** | 25 API 호출 |
| 유튜브 | YouTube Data API v3 | 영상 업로드만 (이미지 게시 불가) | OAuth 2.0 (Google) | quota 10,000 / 업로드 1회=1600 |
| 틱톡 | TikTok Content Posting API | 영상 업로드만. "Direct Post"는 별도 신청 필요 | OAuth 2.0 (TikTok for Developers) | Direct Post 권한 받기 전엔 "Upload" → 앱에서 사용자가 최종 게시 |
| 네이버 블로그 | **공식 API 없음** (제휴 파트너만) | Selenium/Playwright 반자동 (계정 정지 리스크 큼) | ID/PW + 2FA | — |

> **이미지 캐러셀 게시 가능 = 스레드 + 인스타그램**
> **영상 변환 필수 = 유튜브 + 틱톡**
> **반자동(Chrome MCP)만 가능 = 네이버 블로그**

---

## 3. 폴더 구조 (신규)

```
C:\Users\di898\Documents\phonespot_cardnews\
└─ upload\                                ← 신규
   ├─ .env                                ← API 키 (절대 git에 올리지 말 것)
   ├─ .env.example                        ← 키 이름만 적힌 템플릿
   ├─ requirements.txt                    ← requests, google-api-python-client, playwright
   ├─ tokens\                             ← OAuth 토큰 캐시 (gitignore)
   │  ├─ threads_token.json
   │  ├─ instagram_token.json
   │  ├─ youtube_token.json
   │  └─ tiktok_token.json
   ├─ scripts\
   │  ├─ upload_orchestrator.py           ← 메인 진입점 (채널 선택 + 스케줄 처리)
   │  ├─ caption_parser.py                ← captions.md → 채널별 dict
   │  ├─ channels\
   │  │  ├─ threads.py
   │  │  ├─ instagram.py
   │  │  ├─ youtube.py
   │  │  ├─ tiktok.py
   │  │  └─ naver_blog.py                 ← Playwright/Chrome MCP 반자동
   │  └─ utils\
   │     ├─ env_loader.py                 ← python-dotenv
   │     └─ token_refresh.py              ← OAuth 토큰 갱신 공통
   ├─ logs\
   │  └─ upload_<slug>_<timestamp>.log
   └─ README.md                           ← 사용법 (uploader.py 실행)
```

---

## 4. 환경 변수 (`.env` 템플릿)

```dotenv
# ───── 공용 ─────
LITTLY=https://littly.com/phonespot-gwanggyo
PRECON_URL=https://ictmarket.or.kr/사전승낙서URL

# ───── 스레드 (Meta) ─────
META_APP_ID=
META_APP_SECRET=
THREADS_USER_ID=
THREADS_ACCESS_TOKEN=             # long-lived 60일 토큰

# ───── 인스타그램 (Graph API) ─────
INSTAGRAM_BUSINESS_ACCOUNT_ID=
INSTAGRAM_ACCESS_TOKEN=           # Page Access Token (long-lived)

# ───── 유튜브 ─────
YOUTUBE_CLIENT_SECRETS_PATH=./tokens/yt_client_secret.json
YOUTUBE_CHANNEL_ID=

# ───── 틱톡 ─────
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=
TIKTOK_ACCESS_TOKEN=

# ───── 네이버 블로그 (반자동) ─────
NAVER_ID=
NAVER_PW=                         # 권장: 환경변수 대신 OS Keychain 사용
```

> **보안 원칙**
> - `.env` `tokens/` `logs/` 는 `.gitignore` 필수
> - PW는 평문 저장 피하고 Windows Credential Manager 또는 macOS Keychain 활용 권장
> - Anthropic Cowork은 `.env`를 자동으로 디렉토리 외부 전송하지 않지만, 코드 안에 절대 print/log 하지 말 것

---

## 5. 채널별 구현 가이드

### 5-1. 스레드 (가장 쉬움 — 우선 1순위)

**필요 권한**: `threads_basic`, `threads_content_publish`
**토큰 발급**: https://developers.facebook.com/apps/ → 새 앱 → Threads API 추가 → User Token Generator

**게시 흐름 (2단계)**:
```python
# 단일 이미지
container = POST https://graph.threads.net/v1.0/{user_id}/threads
  ?media_type=IMAGE&image_url={public_url}&text={caption}&access_token={token}
# → returns creation_id

publish = POST https://graph.threads.net/v1.0/{user_id}/threads_publish
  ?creation_id={creation_id}&access_token={token}
```

**카드 6장 캐러셀**: `media_type=CAROUSEL` + 자식 컨테이너 6개 (이미지마다 IS_CAROUSEL_ITEM=true)

**주의**:
- `image_url`은 공개 접근 가능 URL이어야 함 → 로컬 파일은 게시 불가
- → 해결책: AWS S3, Cloudflare R2, 또는 임시 ngrok 터널 + 로컬 HTTP 서버 (로컬 운영 시)
- 카드뉴스 6장이면 R2 같은 정적 호스팅에 자동 업로드 후 URL 반환받는 helper 필요

### 5-2. 인스타그램 (캐러셀)

**선행 작업**:
1. 인스타그램 앱에서 **프로페셔널 계정(비즈니스)** 으로 전환
2. Facebook 페이지와 연동 (Meta Business Suite)
3. https://developers.facebook.com/apps/ → Instagram Graph API 권한 추가
4. 권한: `instagram_basic`, `instagram_content_publish`, `pages_read_engagement`

**캐러셀 게시 흐름 (3단계)**:
```python
# 1. 각 이미지마다 컨테이너 6개 생성
for img in cards:
    POST /{ig-user-id}/media
        ?image_url={public_url}&is_carousel_item=true&access_token={token}
    # → child_creation_id

# 2. 캐러셀 컨테이너 생성
POST /{ig-user-id}/media
    ?media_type=CAROUSEL&children={comma_separated_child_ids}
    &caption={caption}&access_token={token}
# → carousel_creation_id

# 3. 게시
POST /{ig-user-id}/media_publish
    ?creation_id={carousel_creation_id}&access_token={token}
```

**주의**:
- 캡션 길이 2,200자 제한 / 해시태그 30개 제한
- 이미지 비율 1:1 권장 → `output/<slug>/1x1/card_*.jpg` 사용
- 이미지 호스팅 URL 필요 (스레드와 동일)
- 4시간 내 캐러셀 컨테이너 publish 안 하면 만료

### 5-3. 유튜브 Shorts

**선행 작업**:
1. https://console.cloud.google.com/ → 새 프로젝트 → YouTube Data API v3 활성화
2. OAuth 2.0 클라이언트 ID 발급 → `yt_client_secret.json` 다운로드 → `tokens/` 폴더에 저장
3. 첫 실행 시 OAuth 동의 화면 → 토큰 캐시 자동 생성

**업로드 코드 (google-api-python-client)**:
```python
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
flow = InstalledAppFlow.from_client_secrets_file("yt_client_secret.json", SCOPES)
creds = flow.run_local_server(port=0)  # 첫 실행만

youtube = build("youtube", "v3", credentials=creds)

request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": "통신3사 1분기 실적 명암 #Shorts",
            "description": yt_caption,        # captions.md의 유튜브 섹션
            "tags": ["통신3사", "SKT", "LGU+", "KT", "폰스팟광교점"],
            "categoryId": "22",                # People & Blogs
        },
        "status": {"privacyStatus": "public"},
    },
    media_body=MediaFileUpload("output/<slug>/video.mp4", chunksize=-1, resumable=True),
).execute()
```

**Shorts 판정 조건**:
- 영상 길이 ≤ 60초
- 세로 비율 9:16 (1080×1920)
- 제목/설명에 `#Shorts` 포함 (필수는 아니지만 권장)

**Quota 주의**:
- 일 quota 10,000 / 업로드 1회 = 1,600 → 최대 6회/일
- 카드뉴스용 1주 1회 페이스면 충분

### 5-4. 틱톡

**선행 작업**:
1. https://developers.tiktok.com/ → 앱 등록
2. Sandbox 모드에서 테스트 가능
3. 권한 신청:
   - `video.upload` (기본): 영상 업로드만, 사용자가 앱에서 최종 게시
   - `video.publish` (Direct Post): 별도 신청, 심사 통과 시 자동 게시

**Direct Post가 안 될 경우 (대부분 케이스)**:
- 사용자가 TikTok 앱에서 "최근 업로드" 알림을 받고 직접 캡션/태그 입력 후 게시
- 자동화 한계점

**코드 (Upload + Direct Post)**:
```python
# 1. 영상 업로드 초기화
init = requests.post(
    "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/",
    headers={"Authorization": f"Bearer {token}"},
    json={"source_info": {"source": "FILE_UPLOAD", "video_size": size, ...}}
)
# → upload_url 반환

# 2. 영상 PUT 업로드
requests.put(upload_url, data=video_bytes,
             headers={"Content-Type": "video/mp4", "Content-Range": ...})

# 3. (Direct Post 권한이 있다면) 게시
publish = requests.post(
    "https://open.tiktokapis.com/v2/post/publish/video/init/",
    headers={"Authorization": f"Bearer {token}"},
    json={"post_info": {"title": title, "privacy_level": "PUBLIC_TO_EVERYONE", ...},
          "source_info": {...}}
)
```

### 5-5. 네이버 블로그 (반자동)

**자동화 불가능한 이유**:
- 공식 API는 제휴 파트너 신청자만 (개인 사업자 통상 거절)
- Selenium 자동 로그인은 캡차/2FA + 이상 트래픽 탐지 → **계정 정지 위험 큼**

**현실적 대안 — Chrome MCP 반자동**:
1. Cowork의 `mcp__claude-in-chrome__*` 도구로 네이버 블로그 에디터 열기
2. 사용자가 직접 로그인 (또는 이미 로그인된 세션 활용)
3. Claude가 captions.md의 네이버 블로그 섹션을 자동 입력 (제목, 본문, 태그)
4. 이미지 6장(`output/<slug>/4x5/card_*.jpg`)을 순서대로 드래그&드롭 자동화
5. **발행 버튼은 사용자가 직접 클릭** (안전장치)

→ 즉, "본문 입력까지만 자동, 발행은 수동" 모델

---

## 6. 게시 스케줄러

**옵션 A — 즉시 실행 (간단)**:
```bash
python upload\scripts\upload_orchestrator.py --slug telco3_q1_2026 --channels threads,instagram
```

**옵션 B — 예약 (cowork-scheduled-tasks)**:
- `mcp__scheduled-tasks__create_scheduled_task` 활용
- 예: 매주 화/목 오전 10시 / 가장 최근 `articles/*.json` 자동 업로드
- 한국 시간 기준 SNS 최적 게시 시간:
  - 인스타그램: 화·수 11:00, 14:00
  - 스레드: 수·금 13:00, 19:00
  - 유튜브 Shorts: 토·일 18:00~20:00
  - 틱톡: 화·목·일 19:00~21:00
  - 네이버 블로그: 화·수 10:00~11:00 (검색 노출 최적)

**옵션 C — GitHub Actions / Windows Task Scheduler**: 외부 트리거로 실행 시

---

## 7. 실행 순서 (권장)

```
[Day 1] 환경 셋업
  1. upload/ 폴더 생성 + .env 작성
  2. pip install -r requirements.txt
  3. .gitignore에 .env, tokens/, logs/ 추가

[Day 2~3] 스레드 (가장 쉬움)
  1. Meta 개발자 콘솔에서 앱 생성 + Threads API 권한
  2. 이미지 호스팅 셋업 (Cloudflare R2 무료 plan 또는 ngrok)
  3. scripts/channels/threads.py 작성 + 테스트 게시
  4. 운영 시작

[Day 4~5] 인스타그램
  1. 비즈니스 계정 전환 + Facebook 페이지 연동
  2. Graph API 권한 추가
  3. scripts/channels/instagram.py 작성 + 캐러셀 테스트
  4. 운영 시작

[Day 6~7] 유튜브 (SHORTS 테스크 완성 후)
  1. Google Cloud Console에서 OAuth 클라이언트
  2. scripts/channels/youtube.py 작성
  3. 운영 시작

[Day 8~] 틱톡
  1. 개발자 등록 + Direct Post 권한 신청 (심사 1~2주)
  2. 권한 받기 전까지는 Upload만 사용 (반자동)
  3. scripts/channels/tiktok.py 작성

[마지막] 네이버 블로그 (반자동)
  1. scripts/channels/naver_blog.py 작성 (Chrome MCP 또는 Playwright)
  2. 본문 자동 입력 + 발행은 수동 운영
```

---

## 8. 보안 체크리스트

- [ ] `.env` 파일이 `.gitignore`에 포함되어 있는가?
- [ ] `tokens/` 폴더가 `.gitignore`에 포함되어 있는가?
- [ ] `logs/` 폴더에 토큰/PW가 평문으로 기록되지 않는가? (`print(token)` 금지)
- [ ] OAuth 토큰 만료 시 자동 갱신 로직이 있는가? (Meta 60일 / Google refresh_token)
- [ ] 네이버 PW는 평문 저장 대신 Windows Credential Manager 사용했는가?
- [ ] 업로드 실패 시 재시도 정책 (exponential backoff)이 있는가?
- [ ] 채널별 일 게시 한도 초과 시 다음날로 큐잉되는가?

---

## 9. 알려진 함정 (실제 운영 시 자주 막히는 부분)

1. **Threads / Instagram 이미지 URL 문제** — 로컬 파일 못 올림. 반드시 공개 URL 필요. Cloudflare R2 무료 plan(월 10GB 송신 무료) 추천.
2. **Instagram 비즈니스 계정 미전환** — 가장 흔한 에러. 개인 계정으로는 Graph API 호출 자체가 거절됨.
3. **YouTube quota 소진** — 잘못된 코드로 retry 반복하면 6번 만에 quota 소진. dry-run 모드 필수.
4. **TikTok Direct Post 거절** — 신청 시 사업자 등록증, 앱 사용 시나리오 영상 등 제출 요구. 대부분 처음엔 거절됨.
5. **네이버 로그인 자동화** — 이상 트래픽 탐지 1회만 잡혀도 계정 30일 정지 가능. **자동 로그인 절대 금지**, 이미 로그인된 세션만 활용.
6. **Token 만료** — Meta 토큰은 60일, TikTok은 24시간 액세스 + 365일 리프레시. 만료 1주 전 갱신 알림 cron 필수.

---

## 10. 다음 Claude/Cowork 세션이 처음 작업 시작할 때 확인할 것

1. `articles/*.json` 중 가장 최근 슬러그 확인 → `output/<slug>/captions.md` 존재 확인
2. `.env`에 채널별 토큰 채워졌는지 확인
3. `python upload\scripts\upload_orchestrator.py --slug <slug> --channels threads --dry-run` 으로 dry-run
4. 실제 게시 전 사용자에게 캡션 미리보기 + "발행하시겠습니까?" 명시적 동의 받기
5. 5채널 동시 게시는 절대 금지 — 1채널씩 순차 실행 + 각 채널 결과 확인 후 다음 진행

---

## 11. 참고 링크 (2026.05 기준)

- Threads API: https://developers.facebook.com/docs/threads/
- Instagram Graph API: https://developers.facebook.com/docs/instagram-api/
- YouTube Data API: https://developers.google.com/youtube/v3
- TikTok Content Posting: https://developers.tiktok.com/doc/content-posting-api-get-started
- Google OAuth 2.0: https://developers.google.com/identity/protocols/oauth2
- Cloudflare R2 (이미지 호스팅): https://developers.cloudflare.com/r2/

---

## 12. 인수인계 메모

- 현재 상태: **문서만 작성된 단계** (코드 작성 전)
- 카드뉴스 생성 코드(`scripts/cardnews_renderer_v2.py`, v9)는 완성·운영 중
- 숏폼 영상 코드(PROJECT_INSTRUCTIONS_SHORTS.md)는 별도 테스크에서 진행
- 업로드 코드는 이 문서를 기반으로 새 Cowork 세션 또는 Claude Code에서 단계별 구현 권장
- **첫 구현 우선순위 = 스레드 (가장 빠르게 효과 확인)**
- 우선 1채널(스레드)만 자동화하고 나머지는 반자동(사용자가 게시 버튼 클릭)으로 시작하는 것이 안전
