@echo off
setlocal
chcp 65001 >nul
title PhoneSpot Codex - Setup Local Render PC From GitHub

echo ============================================================
echo  PhoneSpot Codex - Local Render PC Setup
echo ============================================================
echo.
echo This script clones the PhoneSpot video system to this PC.
echo Render work will run locally on this PC.
echo.

set "DEFAULT_DIR=C:\PhoneSpot\phonespot_cardnews"
set /p "REPO_URL=GitHub repository URL: "
if "%REPO_URL%"=="" (
  echo [ERROR] Repository URL is required.
  pause
  exit /b 1
)

set /p "TARGET_DIR=Install folder [%DEFAULT_DIR%]: "
if "%TARGET_DIR%"=="" set "TARGET_DIR=%DEFAULT_DIR%"

where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Git is not installed.
  echo Install Git for Windows first: https://git-scm.com/download/win
  pause
  exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js is not installed.
  echo Install Node.js LTS first: https://nodejs.org/
  pause
  exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python is not installed.
  echo Install Python 3.11+ first.
  pause
  exit /b 1
)

if exist "%TARGET_DIR%\.git" (
  echo [INFO] Existing Git folder found. Pull latest.
  git -C "%TARGET_DIR%" pull --ff-only
) else (
  if exist "%TARGET_DIR%" (
    echo [ERROR] Target folder exists but is not a Git repo:
    echo         %TARGET_DIR%
    echo Choose an empty folder or remove it first.
    pause
    exit /b 1
  )
  git clone "%REPO_URL%" "%TARGET_DIR%"
)
if errorlevel 1 (
  echo [ERROR] Git clone/pull failed.
  pause
  exit /b 1
)

cd /d "%TARGET_DIR%\shorts"
if exist package.json (
  echo [deps] npm install
  call npm install
  if errorlevel 1 (
    echo [ERROR] npm install failed.
    pause
    exit /b 1
  )
)

python -m pip install -q edge-tts mutagen

echo.
echo [OK] Setup complete.
echo Start panel:
echo %TARGET_DIR%\CODEX_VIDEO_DESK\00_PHONE_SPOT_PANEL.bat
echo.
pause
