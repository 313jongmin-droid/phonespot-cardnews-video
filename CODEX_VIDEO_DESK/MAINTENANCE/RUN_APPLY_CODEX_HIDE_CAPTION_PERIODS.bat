@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Hide Caption Sentence Periods
echo ============================================================
echo.
python APPLY_CODEX_HIDE_CAPTION_PERIODS.py
if errorlevel 1 (
  echo.
  echo [ERROR] Caption period guard install failed.
  pause
  exit /b 1
)
echo.
echo [OK] Caption period guard installed.
pause
