@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Apply TTS Pronunciation + Timing Layer
echo ============================================================
echo.
python APPLY_CODEX_TTS_PRONUNCIATION_TIMING.py
if errorlevel 1 (
  echo.
  echo [ERROR] TTS pronunciation and timing patch failed.
  pause
  exit /b 1
)
echo.
echo [OK] Patch installed. Render one sample before accepting it.
pause

