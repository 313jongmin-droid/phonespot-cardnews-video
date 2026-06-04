@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Roll Back Korean Caption Compiler V2
echo ============================================================
echo.
py "%~dp0ROLLBACK_CODEX_KOREAN_CAPTION_COMPILER_V2.py"
if errorlevel 1 (
  echo.
  echo [ERROR] Korean caption compiler V2 rollback failed.
  pause
  exit /b 1
)
echo.
pause

