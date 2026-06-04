@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Rollback List Caption Layout Guard
echo ============================================================
echo.
python ROLLBACK_CODEX_LIST_CAPTION_LAYOUT.py
if errorlevel 1 (
  echo.
  echo [ERROR] List caption layout rollback failed.
  pause
  exit /b 1
)
echo.
echo [OK] List caption layout layer rolled back.
pause
