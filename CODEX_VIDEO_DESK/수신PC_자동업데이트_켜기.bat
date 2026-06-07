@echo off
chcp 65001 >nul
rem 부사수(수신) PC에서만 실행. 패널 시작 시 자동으로 git pull(--ff-only) 수행.
rem 대표(개발) PC에서는 실행하지 마세요.
set "HERE=%~dp0"
set "MARKDIR=%HERE%TEMP\panel"
if not exist "%MARKDIR%" mkdir "%MARKDIR%" >nul 2>&1
> "%MARKDIR%\auto_update.on" echo on
echo [OK] 자동 업데이트 ON
echo  - 이제 00_PHONE_SPOT_PANEL.bat 실행 시 git pull 을 먼저 수행합니다.
echo  - 끄려면 같은 폴더의 "수신PC_자동업데이트_끄기.bat" 실행.
echo  - 로그: CODEX_VIDEO_DESK\TEMP\panel\panel_logs\auto_update.log
pause
