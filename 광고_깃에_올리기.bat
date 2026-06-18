@echo off
setlocal enabledelayedexpansion
title PhoneSpot - push apps_script to GitHub
cd /d C:\backup\phonespot_cardnews

rem  Local PC ONLY (push). Scoped to apps_script -> GitHub Actions clasp deploy.

set "GIT="
where git >nul 2>&1 && set "GIT=git"
if not defined GIT if exist "C:\Program Files\Git\cmd\git.exe" set "GIT=C:\Program Files\Git\cmd\git.exe"
if not defined GIT if exist "C:\Program Files\Git\bin\git.exe" set "GIT=C:\Program Files\Git\bin\git.exe"
if not defined GIT if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" set "GIT=%LOCALAPPDATA%\Programs\Git\cmd\git.exe"
if not defined GIT for /d %%D in ("%LOCALAPPDATA%\GitHubDesktop\app-*") do if exist "%%D\resources\app\git\cmd\git.exe" set "GIT=%%D\resources\app\git\cmd\git.exe"
if not defined GIT (
  echo [ERROR] git not found. Install Git for Windows: winget install --id Git.Git -e
  pause
  exit /b 1
)
echo [git] using: !GIT!

rem  one-time local setup (safe to repeat)
"!GIT!" config --global --add safe.directory C:/backup/phonespot_cardnews
"!GIT!" config user.email "313jongmin@gmail.com"
"!GIT!" config user.name "313jongmin-droid"

rem  clear stale lock if present
if exist ".git\index.lock" del ".git\index.lock"

set "MSG=%~1"
if "%MSG%"=="" set "MSG=fix(ads): apps_script update"

"!GIT!" add apps_script
"!GIT!" commit -m "!MSG!"
echo [git] push origin main ...
"!GIT!" push origin main
echo.
echo Done. Look above for "main -> main" (success) or errors.
pause
