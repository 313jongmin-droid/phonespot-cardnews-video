@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title PhoneSpot assistant PC one-click setup (standalone full producer)

rem Run this single file on a fresh PC:
rem   1) install Git / Node.js / Python (winget)
rem   2) clone the project from GitHub (or pull)
rem   3) install full deps (cardnews + video) and verify
rem Works before clone. Copy this file to the new PC and double-click.

set "REPO=https://github.com/313jongmin-droid/phonespot-cardnews-video.git"
set "TARGET=C:\PhoneSpot\phonespot_cardnews"

echo ============================================================
echo  PhoneSpot assistant PC one-click setup
echo  install dir: %TARGET%
echo  repo       : %REPO%
echo ============================================================
echo.

echo ===== 1/4: ensure Git / Node.js / Python =====
call :ensure git     "Git.Git"            "Git"
call :ensure node    "OpenJS.NodeJS.LTS"  "Node.js"
call :ensure python  "Python.Python.3.12" "Python"

where git >nul 2>&1
if errorlevel 1 (
  echo.
  echo [ERROR] Git not found. If you just installed it, close this window
  echo         and run this file again (PATH needs refresh^).
  pause & exit /b 1
)

echo.
echo ===== 2/4: get project (clone / pull) =====
if exist "%TARGET%\.git" (
  echo [update] existing repo - git pull --ff-only
  git -C "%TARGET%" pull --ff-only
) else (
  for %%I in ("%TARGET%\..") do if not exist "%%~fI" mkdir "%%~fI" >nul 2>&1
  echo [clone] %REPO%
  git clone "%REPO%" "%TARGET%"
)

if not exist "%TARGET%\CODEX_VIDEO_DESK\SETUP_FULL_PRODUCER.bat" (
  echo.
  echo [ERROR] SETUP_FULL_PRODUCER.bat missing after clone.
  echo         Check network / repo access.
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

rem 4-1) install Google Drive desktop (skip if already installed)
where winget >nul 2>&1 && (
  echo [install] Google Drive desktop (skip if present)
  winget install --id Google.GoogleDrive -e --source winget --accept-package-agreements --accept-source-agreements
)
echo.
echo  [MANUAL — cannot be automated for security/account reasons]
echo   1) Log in to Google Drive desktop with the shared account.
echo   2) In Drive, right-click the shared "PhoneSpot_Library" folder
echo      and choose "Add shortcut to My Drive" (so it syncs locally).
echo   When done, press any key to auto-detect the local path...
pause >nul

set "PYDET=%TARGET%\.phonespot_runtime\Scripts\python.exe"
if not exist "%PYDET%" set "PYDET=python"
"%PYDET%" "%TARGET%\shorts\scripts\codex_detect_drive_hub.py"
if errorlevel 1 (
  echo  [info] auto-detect failed. Run later:
  echo        %TARGET%\CODEX_VIDEO_DESK\일러스트_공유허브_경로설정.bat
)
goto :gddone
:skipgd
echo  [skip] You can set this up later with 일러스트_공유허브_경로설정.bat
:gddone

echo.
echo ===== 5/5: done =====
echo ------------------------------------------------------------
echo  This PC is now a standalone producer (cardnews + video render).
echo.
echo  start        : %TARGET%\CODEX_VIDEO_DESK\00_PHONE_SPOT_PANEL.bat
echo  cardnews     : cardnews tab in the panel
echo  illust sync  : panel "Manage > library sync" (Drive hub)
echo  auto-update  : 수신PC_자동업데이트_켜기.bat (optional)
echo.
echo  NOTE: API keys/tokens are NOT in GitHub. If article generation or
echo        readable concept names need a key, set _secrets\gemini_key.txt
echo        like on the main PC.
echo ------------------------------------------------------------
echo.
pause
exit /b 0

:ensure
rem %1=exe %2=winget id %3=label
where %1 >nul 2>&1
if not errorlevel 1 (
  echo [OK] %3 already installed
  exit /b 0
)
where winget >nul 2>&1
if errorlevel 1 (
  echo [WARN] %3 missing and winget unavailable - install %3 manually, then re-run.
  exit /b 0
)
echo [install] %3 (winget)
winget install --id %2 -e --source winget --accept-package-agreements --accept-source-agreements
exit /b 0
