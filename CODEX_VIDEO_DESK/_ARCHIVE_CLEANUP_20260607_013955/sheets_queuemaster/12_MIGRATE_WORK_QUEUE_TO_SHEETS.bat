@echo off
setlocal
chcp 65001 >nul
title PhoneSpot - Work Queue Migrate To Sheets (1회)

rem 최초 1회만 실행: 현재 로컬 작업 큐의 모든 필드를 구글 시트로 씨딩합니다.
rem 이후에는 11_SYNC_WORK_QUEUE_WITH_SHEETS.bat 만 사용하세요.

pushd "%~dp0" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 패널 폴더에 접근할 수 없습니다: %~dp0
  pause
  exit /b 1
)

echo 현재 로컬 작업 큐를 구글 시트에 씨딩합니다...
python "SHEETS_SYNC\sheets_sync.py" migrate
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" (
  python3 "SHEETS_SYNC\sheets_sync.py" migrate
  set ERR=%ERRORLEVEL%
)

popd
echo.
if "%ERR%"=="0" (
  echo [OK] 씨딩 완료. 이제부터는 11_SYNC_WORK_QUEUE_WITH_SHEETS.bat 로 동기화하세요.
) else (
  echo [ERROR] 씨딩 실패. SHEETS_SYNC\SETUP_SHEETS_QUEUE_MASTER.md 를 확인하세요.
)
pause
exit /b %ERR%
