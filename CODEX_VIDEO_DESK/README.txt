PhoneSpot Codex Video Desk

실행 파일은 2개만 보면 됩니다.

1. 00_PHONE_SPOT_PANEL.bat
   - 제작 패널을 엽니다.
   - 브라우저 주소는 http://localhost:4901/ 입니다.
   - 창은 숨김 실행되며, 패널은 한 번만 열리도록 구성되어 있습니다.

2. 00_SETUP_ASSISTANT_PC.bat
   - 부사수 PC 등 다른 PC에서 최초 1회 실행합니다.
   - 네트워크 공유 폴더에서 실행해도 되도록 pushd 방식으로 동작합니다.
   - Python, Node.js/npm, FFmpeg, edge-tts, npm 패키지를 점검합니다.
   - 설치 후에는 같은 폴더의 00_PHONE_SPOT_PANEL.bat만 실행하면 됩니다.

다른 PC 사용 조건

- 이 폴더를 읽고 쓸 수 있는 네트워크 공유 권한이 필요합니다.
- 렌더링은 실행한 PC의 성능을 사용합니다.
- 결과물은 CODEX_VIDEO_DESK\RESULTS 폴더에 저장됩니다.
- 패널이 안 열리면 00_SETUP_ASSISTANT_PC.bat을 다시 실행해 환경을 점검하세요.

네트워크 공유에서 다른 PC로 실행할 때

- 00_PHONE_SPOT_PANEL.bat은 UNC 경로를 자동으로 임시 드라이브에 연결해 실행합니다.
- 패널 서버의 PID/로그는 실행한 PC의 AppData\Local\PhoneSpotCodexVideo\panel 에 저장됩니다.
- 영상 결과와 작업 데이터는 공유 폴더 CODEX_VIDEO_DESK\RESULTS 에 저장되므로, 공유 권한은 읽기/쓰기 모두 필요합니다.
- 브라우저에 localhost 접속 거부가 뜨면 AppData\Local\PhoneSpotCodexVideo\panel\panel_logs 의 최신 로그를 확인하세요.

