@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Preview Confirmed Junk Cleanup
echo ============================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0CLEAN_CODEX_CONFIRMED_JUNK.ps1"
echo.
pause

