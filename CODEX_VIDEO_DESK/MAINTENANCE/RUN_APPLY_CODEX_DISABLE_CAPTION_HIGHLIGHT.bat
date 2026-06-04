@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Disable Inline Caption Highlights
echo ============================================================
echo.
python APPLY_CODEX_DISABLE_CAPTION_HIGHLIGHT.py
if errorlevel 1 (
  echo.
  echo [ERROR] Caption-highlight disable patch failed.
  pause
  exit /b 1
)
echo.
pause
