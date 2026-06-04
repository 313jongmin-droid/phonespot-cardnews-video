@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Install TTS Controls Into Video Desk
echo ============================================================
echo.
python INSTALL_CODEX_TTS_DESK_BUTTONS.py
if errorlevel 1 (
  echo.
  echo [ERROR] TTS desk button install failed.
  pause
  exit /b 1
)
echo.
echo [OK] Open CODEX_VIDEO_DESK and use button 08.
pause

