@echo off
setlocal
chcp 65001 >nul
title PhoneSpot - Work Queue Sheets Sync

rem 네트워크 공유에서 실행해도 되도록 pushd 로 임시 드라이브 매핑
pushd "%~dp0" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 패널 폴더에 접근할 수 없습니다: %~dp0
  pause
  exit /b 1
)

python "SHEETS_SYNC\sheets_sync.py" sync
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" (
  python3 "SHEETS_SYNC\sheets_sync.py" sync
  set ERR=%ERRORLEVEL%
)

popd
echo.
if "%ERR%"=="0" (
  echo [OK] 작업 큐 - 구글 시트 동기화 완료.
) else (
  echo [ERROR] 동기화 실패. SHEETS_SYNC\SETUP_SHEETS_QUEUE_MASTER.md 를 확인하세요.
)
pause
exit /b %ERR%
