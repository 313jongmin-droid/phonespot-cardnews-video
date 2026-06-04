@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Fixed Caption Font and Visual Rhythm
echo ============================================================
echo.
python APPLY_CODEX_FIXED_CAPTION_RHYTHM.py
if errorlevel 1 (
  echo.
  echo [ERROR] Fixed-caption rhythm patch failed.
  pause
  exit /b 1
)
echo.
pause
