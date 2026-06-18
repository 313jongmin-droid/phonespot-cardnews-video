# PhoneSpot Codex 로컬 렌더 PC 세팅 가이드

목표는 간단합니다.

- GitHub는 코드 업데이트 저장소로만 사용합니다.
- 영상 렌더링은 각 PC의 로컬 폴더에서 실행합니다.
- 부사수 PC가 더 빠르면 부사수 PC에서 렌더링합니다.
- 토큰, 결과 영상, 다운로드 이미지, node_modules 같은 런타임 파일은 GitHub에 올리지 않습니다.

## 권장 구조

대표 PC:

```text
C:\backup\phonespot_cardnews
```

부사수 PC:

```text
C:\PhoneSpot\phonespot_cardnews
```

## 부사수 PC 최초 세팅

아래 파일 하나만 실행합니다.

```text
CODEX_VIDEO_DESK\00_SETUP_RENDER_PC_FROM_GITHUB.bat
```

또는 프로젝트 루트에 있는 파일:

```text
00_SETUP_RENDER_PC_FROM_GITHUB.bat
```

기본 GitHub 저장소:

```text
https://github.com/313jongmin-droid/phonespot-cardnews-video.git
```

세팅 파일이 하는 일:

1. Git, Node.js, Python 설치 여부 확인
2. 없으면 가능한 경우 winget으로 설치 시도
3. GitHub에서 프로젝트 clone 또는 pull
4. `shorts` 의 `npm install` 실행
5. TTS/검증용 Python 패키지 설치
6. 제작 패널 실행

## 업데이트 방식

대표 PC에서 수정 후 GitHub에 push합니다.

부사수 PC는 패널의 `시스템 업데이트` 버튼을 누르거나 아래 파일을 실행합니다.

```text
CODEX_VIDEO_DESK\MAINTENANCE\codex_github_update.py
```

## 주의

- 네트워크 공유 폴더에서 직접 렌더링하지 않습니다.
- 렌더링은 반드시 각 PC의 로컬 폴더에서 합니다.
- 카드뉴스 원본 결과물은 별도 동기화 전략이 필요합니다.
- OAuth 토큰, API 키, 결과 영상은 GitHub에 올리지 않습니다.
## 카드뉴스 결과물 동기화

부사수 PC는 GitHub로 코드는 받을 수 있지만, 카드뉴스 결과물(`cardnews/output`)은 GitHub에 올리지 않습니다.

부사수 PC에서 슬러그가 비어 있으면 아래 파일을 실행하세요.

```text
CODEX_VIDEO_DESK\01_SYNC_CARDNEWS_OUTPUT_FROM_MAIN_PC.bat
```

이 파일은 대표 PC 공유폴더:

```text
\\192.168.0.7\phonespot_cardnews\cardnews\output
```

를 부사수 PC 로컬:

```text
C:\PhoneSpot\phonespot_cardnews\cardnews\output
```

으로 복사합니다.

중요:

- 스크립트 실행은 부사수 PC 로컬에서 합니다.
- 네트워크 공유 폴더에서 렌더링하지 않습니다.
- 목록이 비어 있으면 먼저 동기화하고 패널을 새로고침하세요.

## 자동 카드뉴스 결과물 동기화

부사수 PC에서 `00_PHONE_SPOT_PANEL.bat`을 실행하면 시작 전에 자동으로 대표 PC의 카드뉴스 결과물을 로컬로 가져옵니다.

```text
\\192.168.0.7\phonespot_cardnews\cardnews\output
↓
C:\PhoneSpot\phonespot_cardnews\cardnews\output
```

패널이 이미 켜진 뒤 새 카드뉴스가 추가되었다면 패널을 다시 열거나 수동 동기화 파일을 한 번 실행하면 됩니다.

## 카드뉴스 작업 데이터 전체 동기화

부사수 PC의 슬러그 목록은 `cardnews/output`만으로는 부족할 수 있습니다.
새 카드뉴스는 보통 아래 순서로 생성됩니다.

```text
cardnews/articles  -> 기사 JSON
cardnews/images    -> GPT 생성 이미지
cardnews/output    -> 최종 카드뉴스 렌더 결과
```

그래서 부사수 PC에서는 `00_PHONE_SPOT_PANEL.bat` 실행 시 세 폴더를 모두 동기화합니다.

```text
\\192.168.0.7\phonespot_cardnews\cardnews\articles
\\192.168.0.7\phonespot_cardnews\cardnews\images
\\192.168.0.7\phonespot_cardnews\cardnews\output
```

수동으로 다시 동기화하려면:

```text
CODEX_VIDEO_DESK\01_SYNC_CARDNEWS_WORKSPACE_FROM_MAIN_PC.bat
```

15번처럼 `articles/images`는 있는데 `output`이 아직 없는 경우, 부사수 PC는 카드뉴스 탭에서 카드뉴스 렌더를 먼저 실행한 뒤 영상 작업으로 넘어갈 수 있습니다.

