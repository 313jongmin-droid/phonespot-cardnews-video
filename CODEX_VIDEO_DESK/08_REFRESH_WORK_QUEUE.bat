@echo off
setlocal
chcp 65001 >nul
title PhoneSpot Codex - Work Queue Refresh

set ROOT=%~dp0..
set ROOT=%ROOT:\CODEX_VIDEO_DESK\..=%
python "%ROOT%\shorts\scripts\codex_work_queue.py" --open
if errorlevel 1 (
  echo.
  echo [ERROR] Work queue refresh failed.
  pause
  exit /b 1
)

echo.
echo [OK] Work queue refreshed.
pause
