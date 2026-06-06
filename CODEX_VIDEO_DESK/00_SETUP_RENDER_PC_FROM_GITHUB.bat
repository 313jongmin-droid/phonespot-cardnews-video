@echo off
setlocal
chcp 65001 >nul
title PhoneSpot Codex - Setup Render PC

echo ============================================================
echo  PhoneSpot Codex - Render PC Setup
echo ============================================================
echo.
echo This setup installs the local render workspace on this PC.
echo Press Enter to use the default folder:
echo   C:\PhoneSpot\phonespot_cardnews
echo.

set "DEFAULT_DIR=C:\PhoneSpot\phonespot_cardnews"
set /p "TARGET_DIR=Install folder [%DEFAULT_DIR%]: "
if "%TARGET_DIR%"=="" set "TARGET_DIR=%DEFAULT_DIR%"
echo.
set /p "PANEL_URL=Main PC panel URL [example: http://192.168.0.7:4901]: "
if "%PANEL_URL%"=="" (
  echo [ERROR] Main PC panel URL is required.
  pause
  exit /b 1
)

set "SCRIPT=%~dp000_SETUP_RENDER_PC_FROM_GITHUB.ps1"
if not exist "%SCRIPT%" (
  echo [ERROR] Missing setup script:
  echo %SCRIPT%
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" -TargetDir "%TARGET_DIR%" -PanelUrl "%PANEL_URL%"
if errorlevel 1 (
  echo.
  echo [ERROR] Setup failed.
  echo If a folder was open in Explorer, close it and run this again.
  pause
  exit /b 1
)

echo.
echo [OK] Render PC setup finished.
pause
