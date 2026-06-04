@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Rollback Illustration Tag DB + Recent Use
echo ============================================================
echo.
python ROLLBACK_CODEX_ILLUSTRATION_TAG_DB.py
if errorlevel 1 (
  echo.
  echo [ERROR] Illustration tag DB rollback failed.
  pause
  exit /b 1
)
echo.
echo [OK] Rollback complete.
pause

