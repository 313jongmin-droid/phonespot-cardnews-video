@echo off
chcp 65001 >nul
rem (old name kept for compatibility; identical to 수신PC_자동업데이트_켜기.bat)
rem Run on assistant (receiver) PC only. Panel runs git pull on start.
rem Do NOT run on the main (dev) PC.
set "HERE=%~dp0"
set "MARKDIR=%HERE%TEMP\panel"
if not exist "%MARKDIR%" mkdir "%MARKDIR%" >nul 2>&1
> "%MARKDIR%\auto_update.on" echo on
echo [OK] auto-update ON (marker created)
echo  - Panel will run "git pull" before starting from now on.
echo  - Disable: 수신PC_자동업데이트_끄기.bat
echo  - Log: CODEX_VIDEO_DESK\TEMP\panel\panel_logs\auto_update.log
pause
