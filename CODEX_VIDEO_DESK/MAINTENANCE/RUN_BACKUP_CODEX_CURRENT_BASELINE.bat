@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Backup Current Remotion Baseline
echo ============================================================
echo.
python BACKUP_CODEX_CURRENT_BASELINE.py
if errorlevel 1 (
  echo.
  echo [ERROR] Backup failed.
  pause
  exit /b 1
)
echo.
pause
