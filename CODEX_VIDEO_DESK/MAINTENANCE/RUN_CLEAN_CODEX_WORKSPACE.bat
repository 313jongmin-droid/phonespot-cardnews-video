@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Clean Workspace
echo ============================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0CLEAN_CODEX_WORKSPACE.ps1"
if errorlevel 1 (
  echo.
  echo [ERROR] Cleanup failed. No unchecked external path was deleted.
  pause
  exit /b 1
)
echo.
echo [OK] Cleanup finished.
pause
