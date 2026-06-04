@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0CLEAN_DOCUMENTS_CODEX_JUNK.ps1"
if errorlevel 1 (
  echo.
  echo [ERROR] Codex junk cleanup failed.
  pause
  exit /b 1
)
echo.
echo [OK] Confirmed test junk cleanup finished.
pause
