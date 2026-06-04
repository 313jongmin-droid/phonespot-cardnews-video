@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Install Master Video Guide
echo ============================================================
echo.
python APPLY_CODEX_MASTER_VIDEO_GUIDE.py
if errorlevel 1 (
  echo.
  echo [ERROR] Master video guide install failed.
  pause
  exit /b 1
)
echo.
echo [OK] Master video guide installed.
pause

