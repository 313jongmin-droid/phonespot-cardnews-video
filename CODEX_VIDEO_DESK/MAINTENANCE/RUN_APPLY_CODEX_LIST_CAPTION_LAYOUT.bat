@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Apply List Caption Layout Guard
echo ============================================================
echo.
python APPLY_CODEX_LIST_CAPTION_LAYOUT.py
if errorlevel 1 (
  echo.
  echo [ERROR] List caption layout guard install failed.
  pause
  exit /b 1
)
echo.
echo [OK] List caption layout guard installed.
pause
