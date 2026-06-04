@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Apply Illustration Scout V2.1 Transfer
echo ============================================================
echo.
py "%~dp0APPLY_CODEX_ILLUSTRATION_SCOUT_V21_TRANSFER.py"
if errorlevel 1 (
  echo.
  echo [ERROR] Illustration Scout V2.1 install failed.
  pause
  exit /b 1
)
echo.
pause
