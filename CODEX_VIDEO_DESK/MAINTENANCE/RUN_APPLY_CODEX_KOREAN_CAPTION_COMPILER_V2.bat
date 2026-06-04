@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Apply Korean Caption Compiler V2
echo ============================================================
echo.
py "%~dp0APPLY_CODEX_KOREAN_CAPTION_COMPILER_V2.py"
if errorlevel 1 (
  echo.
  echo [ERROR] Korean caption compiler V2 install failed.
  pause
  exit /b 1
)
echo.
pause

