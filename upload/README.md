# upload/ — SNS 5채널 업로드 자동화

> 상세 설계: `../PROJECT_INSTRUCTIONS_UPLOAD.md`
> 현재 상태: **폴더/스크립트 stub 만 완성, 채널별 실제 구현 전**

---

## 0. 폴더 구조 (현재)

```
upload/
├─ .env.example                 ← 환경변수 템플릿 (실제 키는 .env 로 복사 후 채움)
├─ requirements.txt
├─ README.md (이 파일)
├─ tokens/                       ← OAuth 토큰 캐시 (.gitignore)
│  └─ .gitkeep
├─ logs/                         ← 업로드 로그 (.gitignore)
│  └─ .gitkeep
└─ scripts/
   ├─ upload_orchestrator.py     ← 진입점 (dry-run 동작 OK)
   ├─ caption_parser.py          ← 동작 OK (외부 API 불필요)
   ├─ utils/
   │  ├─ __init__.py
   │  ├─ env_loader.py           ← 동작 OK
   │  └─ token_refresh.py        ← STUB
   └─ channels/
      ├─ __init__.py
      ├─ threads.py              ← STUB
      ├─ instagram.py            ← STUB
      ├─ youtube.py              ← STUB
      ├─ tiktok.py               ← STUB
      └─ naver_blog.py           ← STUB
```

---

## 1. 처음 설치 (Day 1)

```powershell
# 1) 의존성 설치
cd C:\Users\di898\Documents\phonespot_cardnews
python -m pip install -r upload\requirements.txt

# 2) .env 파일 만들기 (실제 키는 아직 비워둬도 됨)
copy upload\.env.example upload\.env

# 3) (선택) Playwright 브라우저 — 네이버 블로그용
python -m playwright install chromium
```

`.env` 와 `tokens/`, `logs/` 는 이미 `.gitignore` 에 포함됨.

---

## 2. 동작 확인 (dry-run)

채널별 실제 게시 로직은 아직 STUB 이지만, 입력 검증과 캡션 파싱은
이미 동작합니다. 가장 최근 슬러그로 dry-run 을 실행해 보세요:

```powershell
python upload\scripts\upload_orchestrator.py ^
    --slug iphone18_spec_downgrade_v2 ^
    --channels threads,instagram ^
    --dry-run
```

기대 출력:
- 카드 6장(`1x1/card_1..6.jpg`) 존재 확인
- `captions.md` 에서 스레드/인스타그램 섹션 분리
- 각 채널 본문 미리보기 (앞 120자)
- 실제 API 호출 없이 종료

> **주의:** 현재 output 디렉토리의 카드는 `.png` 입니다.
> 오케스트레이터는 `.jpg` 를 기대하므로 dry-run 시
> "1x1 카드 누락" 에러가 날 수 있습니다.
> 카드뉴스 렌더러 v9 와 합의된 확장자에 맞춰
> `upload_orchestrator.py` 의 `_resolve_paths` 를 조정하거나,
> 렌더러가 `.jpg` 도 함께 산출하도록 합의 필요.

---

## 3. 다음 단계 (우선순위 순)

문서 섹션 7 의 권장 순서:

1. **Day 2~3 — 스레드 (1순위)**
   - Meta 개발자 앱 생성 + Threads API 권한
   - 이미지 호스팅 셋업 (Cloudflare R2 권장)
   - `scripts/channels/threads.py` 의 STUB 채우기
2. **Day 4~5 — 인스타그램**
   - 비즈니스 계정 전환 + Facebook 페이지 연동
   - Graph API 권한 추가
   - `scripts/channels/instagram.py` 채우기
3. **Day 6~7 — 유튜브 Shorts** (SHORTS 테스크 완성 후)
4. **Day 8~ — 틱톡** (Direct Post 권한 심사 1~2주)
5. **마지막 — 네이버 블로그** (Chrome MCP 반자동)

---

## 4. 보안 체크리스트 (Day 1 에 확인)

- [ ] `.env` 가 `.gitignore` 에 포함 (`upload/.env` 항목)
- [ ] `tokens/` 가 `.gitignore` 에 포함
- [ ] `logs/` 가 `.gitignore` 에 포함
- [ ] `print(token)` 같은 코드가 어디에도 없는지 grep
- [ ] 네이버 PW 는 평문 저장 대신 Windows Credential Manager 사용 검토
- [ ] git 초기화되어 있다면 `.gitignore` 가 .env 보다 먼저 커밋되었는지 확인

---

## 5. 알려진 함정 (요약, 자세한 내용은 PROJECT_INSTRUCTIONS_UPLOAD.md 섹션 9)

- Threads/Instagram 은 **공개 URL 이미지만 게시 가능** — 로컬 파일 불가
- Instagram 은 비즈니스 계정 + Facebook 페이지 연동 필수
- YouTube quota 10,000/일, 1회 업로드=1,600 → 잘못된 retry 로 quota 소진 주의
- TikTok Direct Post 권한은 첫 신청 대부분 거절됨
- 네이버 자동 로그인 = 계정 30일 정지 가능 → 절대 금지

---

## 6. 파일별 구현 상태

| 파일 | 상태 | 비고 |
|---|---|---|
| `.env.example` | ✓ | 실제 `.env` 는 별도 작성 |
| `requirements.txt` | ✓ | |
| `caption_parser.py` | ✓ | 단독 실행 가능 |
| `utils/env_loader.py` | ✓ | python-dotenv 있으면 사용, 없으면 fallback |
| `utils/token_refresh.py` | STUB | 채널 구현 시 함께 진행 |
| `upload_orchestrator.py` | 부분 | dry-run 동작, 실제 게시 호출은 STUB |
| `channels/threads.py` | STUB | **1순위 구현** |
| `channels/instagram.py` | STUB | |
| `channels/youtube.py` | STUB | |
| `channels/tiktok.py` | STUB | |
| `channels/naver_blog.py` | STUB | |
