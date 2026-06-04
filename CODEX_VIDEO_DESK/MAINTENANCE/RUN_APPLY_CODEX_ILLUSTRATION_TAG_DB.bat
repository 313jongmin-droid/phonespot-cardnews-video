@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Apply Illustration Tag DB + Recent Use
echo ============================================================
echo.
python APPLY_CODEX_ILLUSTRATION_TAG_DB.py
if errorlevel 1 (
  echo.
  echo [ERROR] Illustration tag DB patch failed.
  pause
  exit /b 1
)
echo.
echo [OK] Open CODEX_VIDEO_DESK and use button 11.
pause

