@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Move Remaining Tools Into CODEX_VIDEO_DESK
echo ============================================================
echo.
py "%~dp0MIGRATE_CODEX_TO_VIDEO_DESK.py"
if errorlevel 1 (
  echo.
  echo [ERROR] Codex maintenance migration failed.
  pause
  exit /b 1
)
echo.
echo [OK] Codex maintenance migration finished.
echo [NEXT] Open CODEX_VIDEO_DESK and verify the new maintenance buttons.
pause
