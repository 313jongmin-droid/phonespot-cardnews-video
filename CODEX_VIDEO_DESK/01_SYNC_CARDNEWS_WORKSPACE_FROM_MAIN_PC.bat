@echo off
setlocal
chcp 65001 >nul
title PhoneSpot Codex - Sync Cardnews Workspace

set "SCRIPT=%~dp0SYNC_CARDNEWS_WORKSPACE_FROM_MAIN_PC.ps1"
if not exist "%SCRIPT%" (
  echo [ERROR] Missing script:
  echo %SCRIPT%
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
if errorlevel 1 (
  echo.
  echo [ERROR] Cardnews workspace sync failed.
  pause
  exit /b 1
)

echo.
echo [OK] Done.
pause
