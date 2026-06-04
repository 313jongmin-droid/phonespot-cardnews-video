@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Roll Back Illustration Scout V2.1
echo ============================================================
echo.
py "%~dp0ROLLBACK_CODEX_ILLUSTRATION_SCOUT_V21_TRANSFER.py"
if errorlevel 1 (
  echo.
  echo [ERROR] Illustration Scout V2.1 rollback failed.
  pause
  exit /b 1
)
echo.
pause
