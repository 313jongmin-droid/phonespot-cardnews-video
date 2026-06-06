@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "PLAYWRIGHT_BROWSERS_PATH=%~dp0..\.playwright"
if exist "%~dp0..\.phonespot_runtime\Scripts\python.exe" (
  for %%I in ("%~dp0..\.phonespot_runtime\Scripts") do set "PATH=%%~fI;%PATH%"
)

if "%PHONESPOT_PANEL_URL%"=="" (
  if exist "%~dp0RENDER_WORKER\panel_url.txt" (
    set /p PHONESPOT_PANEL_URL=<"%~dp0RENDER_WORKER\panel_url.txt"
  ) else (
    set "PHONESPOT_PANEL_URL=http://127.0.0.1:4901"
  )
)

echo ============================================================
echo  PhoneSpot Render Worker
echo ============================================================
echo Panel: %PHONESPOT_PANEL_URL%
echo.
echo Same PC: leave the default address.
echo Other PC:
echo   set PHONESPOT_PANEL_URL=http://MAIN_PC_IP:4901
echo   01_START_RENDER_WORKER.bat
echo.
echo Stop this window to stop rendering on this PC.
echo.

python RENDER_WORKER\worker.py
pause
