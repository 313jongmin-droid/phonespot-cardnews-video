@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - DESK-ONLY Video Storage
echo ============================================================
echo.
python APPLY_CODEX_RESULTS_PACKAGE_V2.py
if errorlevel 1 (
  echo.
  echo [ERROR] Desk-only video storage install failed.
  pause
  exit /b 1
)
echo.
echo [OK] Desk-only video storage installed.
pause
