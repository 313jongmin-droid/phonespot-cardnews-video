@echo off
chcp 65001 >nul
setlocal
title PhoneSpot - stop tracking runtime files (one-time, MAIN PC)
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
cd /d "%ROOT%"

where git >nul 2>&1 || ( echo [ERROR] git not found. & pause & exit /b 1 )

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
git rm -r --cached --ignore-unmatch "shorts/public/assets/illustrations"
git rm --cached --ignore-unmatch "shorts/config/illustration_tag_db.json"
git rm --cached --ignore-unmatch "shorts/codex/ILLUSTRATION_TAG_DB.md"
git rm --cached --ignore-unmatch "shorts/codex/illustration_usage_history.json"
git rm --cached --ignore-unmatch "shorts/public/shorts_script.json"

git add .gitignore
git commit -m "stop tracking runtime/generated files (prevent pull conflicts)"
if errorlevel 1 echo [info] nothing to commit or commit failed - see above.

echo.
echo [git] push...
git push
if errorlevel 1 (
  echo [FAIL] push failed. Check internet / git credentials.
) else (
  echo [OK] done. Other PCs: next pull is clean. If an illustration looks
  echo      missing there, run panel "Manage > library sync" to restore from the hub.
)
pause
