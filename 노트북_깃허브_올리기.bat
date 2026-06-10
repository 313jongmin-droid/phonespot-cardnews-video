@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"
title PhoneSpot - Laptop push to GitHub (DEV ONLY)

rem ============================================================
rem  LAPTOP ONLY. Commit all local changes and push to GitHub.
rem  Office / assistant PC must NOT run this (it is pull-only).
rem  See CLAUDE.md STEP 0 (laptop = push only, exec PC = pull only).
rem ============================================================

set "GIT="
where git >nul 2>&1 && set "GIT=git"
if not defined GIT if exist "C:\Program Files\Git\cmd\git.exe" set "GIT=C:\Program Files\Git\cmd\git.exe"
if not defined GIT if exist "C:\Program Files\Git\bin\git.exe" set "GIT=C:\Program Files\Git\bin\git.exe"
if not defined GIT for /d %%D in ("%LOCALAPPDATA%\GitHubDesktop\app-*") do if exist "%%D\resources\app\git\cmd\git.exe" set "GIT=%%D\resources\app\git\cmd\git.exe"
if not defined GIT (
  echo [ERROR] Git not found. Install Git for Windows or GitHub Desktop, then re-run.
  pause & exit /b 1
)

echo ============================================================
echo  Laptop -^> GitHub push
echo ============================================================
echo.
echo Current changes:
"!GIT!" status --short
echo.

set "MSG="
set /p "MSG=Commit message (press Enter for auto timestamp): "
if "%MSG%"=="" set "MSG=laptop update %DATE% %TIME%"

"!GIT!" add -A
"!GIT!" commit -m "%MSG%"
if errorlevel 1 echo [info] nothing new to commit - will still push any unpushed commits.

echo.
echo === git push origin main ===
"!GIT!" push origin main
if errorlevel 1 (
  echo.
  echo [ERROR] Push failed.
  echo   * "non-fast-forward" = GitHub has newer commits ^(office/codex pushed^).
  echo       Run:  git pull --rebase origin main   then run this file again.
  echo   * Auth prompt = sign in as the GitHub account that owns the repo.
  pause & exit /b 1
)
echo.
echo [OK] Pushed to GitHub. The exec PC can now: git pu