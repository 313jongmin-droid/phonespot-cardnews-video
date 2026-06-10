@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title PhoneSpot assistant PC one-click setup

rem Run on a FRESH assistant PC. Copy this file to a LOCAL disk (Desktop)
rem and double-click. Do NOT run from a network path.
rem Does: install Git/Node/Python (winget) -> clone -> full deps -> optional Google Drive.

set "SELFDIR=%~dp0"
if "%SELFDIR:~0,2%"=="\\" (
  echo [IMPORTANT] You are running from a NETWORK path:
  echo   %SELFDIR%
  echo Copy this .bat to your local Desktop and run it there.
  echo.
  pause
  exit /b 1
)

set "REPO=https://github.com/313jongmin-droid/phonespot-cardnews-video.git"
set "TARGET=C:\PhoneSpot\phonespot_cardnews"

echo ============================================================
echo  PhoneSpot assistant PC one-click setup
echo  install dir: %TARGET%
echo ============================================================
echo.

echo ===== 1/5: ensure Git / Node.js / Python =====
call :ensure git     "Git.Git"            "Git"
call :ensure node    "OpenJS.NodeJS.LTS"  "Node.js"
call :ensure python  "Python.Python.3.12" "Python"

set "GIT="
where git >nul 2>&1 && set "GIT=git"
if not defined GIT if exist "C:\Program Files\Git\cmd\git.exe" set "GIT=C:\Program Files\Git\cmd\git.exe"
if not defined GIT if exist "C:\Program Files\Git\bin\git.exe" set "GIT=C:\Program Files\Git\bin\git.exe"
if not defined GIT for /d %%D in ("%LOCALAPPDATA%\GitHubDesktop\app-*") do if exist "%%D\resources\app\git\cmd\git.exe" set "GIT=%%D\resources\app\git\cmd\git.exe"
if not defined GIT (
  echo.
  echo [ERROR] Git not found. If you just installed it, close this window
  echo         and run this file again ^(PATH needs refresh^).
  pause & exit /b 1
)

echo.
echo ===== 2/5: get project (clone / pull) =====
if exist "%TARGET%\.git" (
  echo [update] existing repo - stash local runtime changes, then pull
  "!GIT!" -C "%TARGET%" stash --include-untracked >nul 2>&1
  "!GIT!" -C "%TARGET%" pull --ff-only
) else (
  for %%I in ("%TARGET%\..") do if not exist "%%~fI" mkdir "%%~fI" >nul 2>&1
  echo [clone] %REPO%
  "!GIT!" clone "%REPO%" "%TARGET%"
)

if not exist "%TARGET%\CODEX_VIDEO_DESK\SETUP_FULL_PRODUCER.bat" (
  echo.
  echo [ERROR] SETUP_FULL_PRODUCER.bat missing after clone. Check network / repo access.
  pause & exit /b 1
)

echo.
echo ===== 3/5: full producer deps + verify =====
echo (npm / python deps / playwright chromium / embedding models ~1GB. takes a while)
call "%TARGET%\CODEX_VIDEO_DESK\SETUP_FULL_PRODUCER.bat"

echo.
echo ===== 4/5: Google Drive illustration sharing (optional) =====
set /p DOGD=Set up Google Drive illustration sharing now? (Y/N):
if /i not "%DOGD%"=="Y" goto :skipgd
where winget >nul 2>&1 && (
  echo [install] Google Drive desktop (skip if present)
  winget install --id Google.GoogleDrive -e --source winget --accept-package-agreements --accept-source-agreements
)
echo.
echo  [MANUAL - cannot be automated for account/security reasons]
echo   1) Log in to Google Drive desktop with the shared account.
echo   2) In Drive, right-click the shared "PhoneSpot_Library" folder
echo      and choose "Add shortcut to My Drive" so it syncs locally.
echo   When done, press any key to auto-detect the local path...
pause >nul
set "PYDET=%TARGET%\.phonespot_runtime\Scripts\python.exe"
if not exist "%PYDET%" set "PYDET=python"
"%PYDET%" "%TARGET%\shorts\scripts\codex_detect_drive_hub.py"
if errorlevel 1 echo  [info] auto-detect failed. Run later: CODEX_VIDEO_DESK\illust hub path setup .bat
goto :gddone
:skipgd
echo  [skip] You can set this up later with the illustration hub path setup .bat
:gddone

echo.
echo ===== 5/5: done =====
echo ------------------------------------------------------------
echo  This PC is now a standalone producer (cardnews + video render).
echo  start       : %TARGET%\CODEX_VIDEO_DESK\00_PHONE_SPOT_PANEL.bat
echo  illust sync : panel "Manage > library sync" (Drive hub)
echo  NOTE: API keys are NOT in GitHub. For article gen / readable concept
echo        names, set _secrets\gemini_key.txt like on the main PC.
echo ----------------