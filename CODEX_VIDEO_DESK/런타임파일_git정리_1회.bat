@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title PhoneSpot - stop tracking runtime files (one-time, MAIN PC)
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
cd /d "%ROOT%"

rem ---- resolve git like the panel does (PATH, Program Files, GitHub Desktop) ----
set "GIT="
where git >nul 2>&1 && set "GIT=git"
if not defined GIT if exist "C:\Program Files\Git\cmd\git.exe" set "GIT=C:\Program Files\Git\cmd\git.exe"
if not defined GIT if exist "C:\Program Files\Git\bin\git.exe" set "GIT=C:\Program Files\Git\bin\git.exe"
if not defined GIT for /d %%D in ("%LOCALAPPDATA%\GitHubDesktop\app-*") do if exist "%%D\resources\app\git\cmd\git.exe" set "GIT=%%D\resources\app\git\cmd\git.exe"
if not defined GIT ( echo [ERROR] git not found. Install Git or GitHub Desktop, then retry. & pause & exit /b 1 )
echo [git] using: !GIT!

echo ============================================================
echo  Stop tracking runtime/generated files in git (one-time).
echo  - Prevents "local changes / untracked would be overwritten" on pull.
echo  - Keeps your local files; only removes them from git tracking.
echo  - Run on the MAIN PC only.
echo.
echo  BEFORE running: make sure illustrations are synced to the Drive hub
echo  (panel "Manage > library sync"), so other PCs can restore them.
echo ============================================================
echo.
set /p OK=Proceed? (Y/N):
if /i not "%OK%"=="Y" ( echo canceled. & pause & exit /b 1 )

echo.
echo [git] untracking runtime files (files stay on disk)...
"!GIT!" rm -r --cached --ignore-unmatch "shorts/public/assets/illustrations"
"!GIT!" rm --cached --ignore-unmatch "shorts/config/illustration_tag_db.json"
"!GIT!" rm --cached --ignore-unmatch "shorts/codex/ILLUSTRATION_TAG_DB.md"
"!GIT!" rm --cached --ignore-unmatch "shorts/codex/illustration_usage_history.json"
"!GIT!" rm --cached --ignore-unmatch "shorts/public/shorts_script.json"

"!GIT!" add .gitignore
"!GIT!" commit -m "stop tracking runtime/generated files