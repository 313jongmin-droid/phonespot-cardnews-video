@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Install Korean Desk README
echo ============================================================
echo.
python INSTALL_CODEX_DESK_KOREAN_README.py
if errorlevel 1 (
  echo.
  echo [ERROR] Korean README install failed.
  pause
  exit /b 1
)
echo.
echo [OK] Korean README installed.
pause
