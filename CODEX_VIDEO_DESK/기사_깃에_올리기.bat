@echo off
chcp 65001 >nul
rem Run on the MAIN PC: push article (topic) JSON + .gitignore to GitHub.
rem Assistant PC receives via git pull (or 수신PC_자동업데이트_켜기.bat).
setlocal
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
cd /d "%ROOT%"

where git >nul 2>&1 || ( echo [ERROR] git not found. Install Git, then retry. & pause & exit /b 1 )

echo [git] add: cardnews\articles + .gitignore
git add cardnews/articles .gitignore

git commit -m "update articles (topic JSON)"
if errorlevel 1 echo [info] nothing new to commit, or commit failed - see above.

echo [git] push...
git push
if errorlevel 1 (
  echo.
  echo [FAIL] push failed. Check internet / git credentials.
) else (
  echo.
  echo [OK] pushed. Assistant PC gets topics via git pull.
)
pause
