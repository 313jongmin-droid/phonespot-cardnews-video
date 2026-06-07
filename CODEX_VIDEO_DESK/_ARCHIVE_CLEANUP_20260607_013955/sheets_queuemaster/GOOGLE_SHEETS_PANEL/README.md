# PhoneSpot Google Sheets Panel MVP

목표: Google Sheets 안에서 제작 패널을 열고, 버튼 클릭으로 현재 PC의 로컬 렌더 엔진을 실행합니다.

## 설치

1. Google Sheets 새 파일 또는 기존 작업대장 파일을 엽니다.
2. `확장 프로그램` > `Apps Script` 를 엽니다.
3. Apps Script에서 파일 2개를 만듭니다.
   - `Code.gs` → 이 폴더의 `Code.gs` 내용 붙여넣기
   - `Sidebar.html` → 이 폴더의 `Sidebar.html` 내용 붙여넣기
4. 저장 후 Google Sheets를 새로고침합니다.
5. 상단 메뉴 `폰스팟 제작` > `제작 패널 열기` 를 누릅니다.

## 사용 전제

- 각 PC에서 로컬 엔진이 켜져 있어야 합니다.
- 보통 `CODEX_VIDEO_DESK`의 최종 실행 파일을 먼저 켭니다.
- 사이드바의 로컬 엔진 주소는 기본 `http://localhost:4878` 입니다.

## 동작 방식

- Google Sheets 사이드바는 화면과 버튼만 담당합니다.
- Remotion/FFmpeg/TTS 렌더링은 버튼을 누른 PC의 로컬 엔진이 담당합니다.
- 시트에는 슬러그 목록과 작업 결과 메모가 기록됩니다.
