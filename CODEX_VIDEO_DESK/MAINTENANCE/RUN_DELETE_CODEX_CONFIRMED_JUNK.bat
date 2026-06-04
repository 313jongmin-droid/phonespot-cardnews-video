@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Delete Confirmed Junk
echo ============================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0CLEAN_CODEX_CONFIRMED_JUNK.ps1" -Apply
if errorlevel 1 (
  echo.
  echo [ERROR] Cleanup failed.
  pause
  exit /b 1
)
echo.
echo [OK] Cleanup finished.
pause

