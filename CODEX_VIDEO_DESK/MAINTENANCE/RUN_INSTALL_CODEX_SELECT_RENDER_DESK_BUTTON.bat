@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Add Select-And-Render Desk Button
echo ============================================================
echo.
python INSTALL_CODEX_SELECT_RENDER_DESK_BUTTON.py
if errorlevel 1 (
  echo.
  echo [ERROR] Desk button install failed.
  pause
  exit /b 1
)
echo.
echo [OK] Button 15 installed in CODEX_VIDEO_DESK.
pause
