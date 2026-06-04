@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Rollback TTS Pronunciation + Timing Layer
echo ============================================================
echo.
python ROLLBACK_CODEX_TTS_PRONUNCIATION_TIMING.py
if errorlevel 1 (
  echo.
  echo [ERROR] Rollback failed.
  pause
  exit /b 1
)
echo.
echo [OK] Rollback complete.
pause

