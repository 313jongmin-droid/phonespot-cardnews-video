@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Disable Downloads Popup In Step 01
echo ============================================================
echo.
python APPLY_CODEX_DESK_NO_DOWNLOADS_POPUP.py
if errorlevel 1 (
  echo.
  echo [ERROR] Downloads popup patch failed.
  pause
  exit /b 1
)
echo.
echo [OK] Step 01 opens the prompt only.
pause
