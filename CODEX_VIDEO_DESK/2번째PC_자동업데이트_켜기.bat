@echo off
chcp 65001 >nul
title 2nd PC - auto update on start (enable)
setx PHONESPOT_AUTO_UPDATE 1 >nul
echo ============================================================
echo  이 PC = "받기 전용"으로 설정했습니다.
echo  이제 00_PHONE_SPOT_PANEL.bat 을 실행할 때마다
echo  자동으로 최신 코드를 받습니다(git pull --ff-only).
echo ============================================================
echo.
echo  주의:
echo   - 메인(개발) PC 에서는 이 파일을 실행하지 마세요.
echo     (작업 중인 변경이 pull 로 덮일 수 있습니다.)
echo   - 끄기:  setx PHONESPOT_AUTO_UPDATE 0   (또는 환경변수 삭제)
echo   - 적용:  지금 켜져 있는 패널을 껐다가 00 으로 다시 켜세요
echo            (환경변수는 새로 여는 창부터 적용됩니다.)
echo   - 의존성(파이썬/노드 패키지)이 바뀐 업데이트면 SETUP_FULL_PRODUCER 를
echo     한 번 다시 돌려야 합니다(코드 pull 만으론 설치가 안 됨).
echo.
pause
