@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - TTS Caption Lockstep
echo ============================================================
echo.
python APPLY_CODEX_TTS_CAPTION_LOCKSTEP.py
if errorlevel 1 (
  echo.
  echo [ERROR] TTS-caption lockstep install failed.
  pause
  exit /b 1
)
echo.
echo [OK] TTS-caption lockstep installed.
pause
