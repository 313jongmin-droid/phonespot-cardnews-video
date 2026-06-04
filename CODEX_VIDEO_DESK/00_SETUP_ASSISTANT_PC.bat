@echo off
chcp 65001 > nul
setlocal

rem This file may be launched from a network share.
rem pushd safely maps UNC paths to a temporary drive letter.
set "DESK_DIR=%~dp0"
pushd "%DESK_DIR%..\shorts" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Cannot enter shorts folder from:
  echo         %DESK_DIR%..\shorts
  echo.
  echo If this is a network share, check sharing permission and reconnect the share.
  pause
  exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found.
  echo Install Python 3.12+ or allow this setup to install it via winget after Python is available.
  popd
  pause
  exit /b 1
)

python scripts\codex_setup_assistant_runtime.py
set "ERR=%ERRORLEVEL%"
popd

if not "%ERR%"=="0" (
  echo.
  echo [ERROR] Assistant PC setup failed.
  pause
  exit /b %ERR%
)

echo.
echo [OK] Assistant PC setup complete.
echo Next: run 00_PHONE_SPOT_PANEL.bat in CODEX_VIDEO_DESK.
pause
exit /b 0
