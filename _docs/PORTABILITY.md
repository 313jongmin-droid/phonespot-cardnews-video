# PORTABILITY — 새 PC 이식 가이드

> 이 폴더 전체를 다른 PC로 복사한 후 30분 안에 작동시키는 가이드.

---

## 1. 폴더 복사

원본 PC에서:
- 폴더 전체 압축: `phonespot_cardnews/` → zip
- 단, **다음은 제외** (용량 절약·재생성 가능):
  - `node_modules/` (npm install로 재생성)
  - `shorts/node_modules/`
  - `cardnews/output/` (재렌더 가능)
  - `shorts/out/`, `shorts/out_codex/` (재빌드 가능)
  - `shorts/public/audio/` (재생성 가능)
  - `_state/logs/` (로그)

새 PC에서 압축 해제 위치: `C:\Users\<사용자명>\Documents\phonespot_cardnews\`
- 다른 경로도 OK (모든 스크립트 상대경로 사용)

---

## 2. 사전 설치

| 항목 | 확인 명령 |
|---|---|
| **Python 3.10+** | `py --version` |
| **Node.js 18+** (쇼츠용) | `node --version` |
| **ffmpeg** (영상 검증) | `ffmpeg -version` |
| **Chrome 최신** | https://www.google.com/chrome/ |

Python 패키지:
```cmd
py -m pip install playwright edge-tts
py -m playwright install chrome
```

Node 패키지 (쇼츠 폴더 안에서):
```cmd
cd shorts
npm install
```

---

## 3. `_secrets/` 키 재발급 (보안상 항상 새로)

원본 PC의 키는 복사하지 말고 새로 발급:

### Gemini API 키
1. https://aistudio.google.com/apikey 접속
2. "Create API key" → 토큰 받기 (AIza... 시작 39자)
3. `_secrets/gemini_key.txt`로 저장

### Telegram 봇
1. 텔레그램 `@BotFather` → `/newbot` → 봇 이름 설정 → 토큰 발급
2. `_secrets/telegram_token.txt`에 저장
3. 텔레그램에서 봇과 `/start` 메시지 1번 보내기
4. `cd automation && py scripts\telegram_notify.py --setup` 실행 → chat_id 자동 추출·저장

---

## 4. Chrome 자동화 프로필 (선택 — Chrome 자동화 쓸 경우만)

```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="C:\Users\<사용자명>\AppData\Local\phonespot_chrome_auto" --profile-directory="Default"
```

새 Chrome 창에서 ChatGPT 로그인 → 창 닫기. 자동화 프로필 준비 완료.

⚠ **사용자명**이 다르면 `automation/scripts/chrome_chatgpt.py`의 `CHROME_USER_DATA_DIR` 경로 수정 필요. (현재 PC = `313jo`로 이미 설정됨)

---

## 5. Windows Task Scheduler 등록 (선택 — 야간 자동화 쓸 경우만)

`automation/night_daemon.bat`을 매일 02:00 실행으로 등록:
1. `taskschd.msc` 열기
2. "기본 작업 만들기" → 이름: `phonespot night daemon`
3. 트리거: 매일 02:00
4. 동작: 프로그램 시작 → `<폴더경로>\automation\night_daemon.bat`
5. 저장

상세는 `_docs/SETUP_WINDOWS.md` 참조.

---

## 6. 첫 실행 검증

```cmd
:: 카드뉴스 렌더링 (Playwright + Chromium 다운로드 약 130MB)
cd cardnews
run_pngs.bat

:: 쇼츠 영상 빌드
cd ..\shorts
run_B_casual.bat

:: 텔레그램 알림 테스트
cd ..\automation
py scripts\telegram_notify.py --test
```

각 단계에서 에러 발생 시:
- `_docs/SETUP_WINDOWS.md` (Windows 환경)
- `_docs/INSTRUCTIONS_CARDNEWS.md` (카드뉴스)
- `shorts/harness/COMMANDS.md` (쇼츠)
- `_docs/BACKUP_HISTORY.md` (트러블슈팅 이력)

---

## 7. 경로 의존성 점검

새 PC 사용자명·드라이브 다르면 다음 파일 확인:

| 파일 | 확인할 것 |
|---|---|
| `automation/scripts/chrome_chatgpt.py` | `CHROME_USER_DATA_DIR`, `CHROME_EXE` 경로 |
| `_secrets/*.txt` | 새 키로 재발급 됐는지 |
| Windows Task Scheduler | bat 파일 절대 경로 |

`run_pngs.bat`, `run_all.bat`, `night_daemon.bat`, 쇼츠 `run_*.bat`은 모두 `cd /d %~dp0`로 자기 위치 기준 작동 → 경로 무관.

Python 스크립트도 모두 `Path(__file__).parent.parent`로 상대경로 → 경로 무관.

---

## 8. 자주 막히는 곳

| 증상 | 원인 | 해결 |
|---|---|---|
| `Playwright not installed` | playwright 패키지 미설치 | `py -m pip install playwright` |
| `Chromium executable doesn't exist` | 브라우저 미설치 | `py -m playwright install chromium` |
| 폰트 깨짐 | Pretendard 로딩 실패 | `cardnews/fonts/` 폴더 안 woff 파일 확인 |
| 텔레그램 전송 실패 | 토큰·chat_id 미설정 | `_secrets/` 점검 |
| 영상 렌더 멈춤 | shorts/node_modules 손상 | `cd shorts && npm install` |

---

## 한 줄 요약

> **폴더 복사 + Python·Node·Chrome 설치 + 키 4종 발급 = 30분 안에 새 PC에서 동일 환경.**
