@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Rollback Caption Period Guard
echo ============================================================
echo.
python ROLLBACK_CODEX_HIDE_CAPTION_PERIODS.py
if errorlevel 1 (
  echo.
  echo [ERROR] Caption period guard rollback failed.
  pause
  exit /b 1
)
echo.
echo [OK] Caption period guard rolled back.
pause
