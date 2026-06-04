@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Apply Publish Package V1
echo ============================================================
echo.
python APPLY_CODEX_PUBLISH_PACKAGE_V1.py
if errorlevel 1 (
  echo.
  echo [ERROR] Publish package V1 install failed.
  pause
  exit /b 1
)
echo.
echo [OK] Publish package V1 installed.
pause
