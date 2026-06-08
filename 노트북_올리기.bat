@echo off
chcp 65001 >nul
rem Laptop dev: push all changes to GitHub. Office PC auto-pulls on panel start.
cd /d "%~dp0"
where git >nul 2>&1 || ( echo [ERROR] git not found. & pause & exit /b 1 )

echo [git] add + commit + push ...
git add -A
git commit -m "dev update from laptop"
if errorlevel 1 echo [info] nothing new to commit (or commit failed).
git push
if errorlevel 1 (
  echo.
  echo [FAIL] push failed - check internet / GitHub login.
) else (
  echo.
  echo [OK] pushed. Office PC gets it on next panel start (auto-pull).
)
pause
