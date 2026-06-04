@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Roll Back Fixed Caption Rhythm
echo ============================================================
echo.
python ROLLBACK_CODEX_FIXED_CAPTION_RHYTHM.py
if errorlevel 1 (
  echo.
  echo [ERROR] Fixed-caption rhythm rollback failed.
  pause
  exit /b 1
)
echo.
pause
