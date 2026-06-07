@echo off
chcp 65001 >nul
rem Register a daily 09:00 illustration-library backup on THIS PC.
rem No admin needed (user task). Skipped on days the PC is off.
set "HERE=%~dp0"
set "RUNCMD=%HERE%dashboard\run_library_backup.cmd"

if not exist "%RUNCMD%" (
  echo [FAIL] missing: %RUNCMD%
  pause
  exit /b 1
)

schtasks /create /tn "PhoneSpot Library Backup" /tr "\"%RUNCMD%\"" /sc DAILY /st 09:00 /f
if errorlevel 1 (
  echo.
  echo [FAIL] schedule register failed. See message above.
) else (
  echo.
  echo [OK] daily 09:00 library backup registered.
  echo  - task name : PhoneSpot Library Backup
  echo  - change time: Task Scheduler ^> "PhoneSpot Library Backup" trigger
  echo  - remove    : 라이브러리_자동백업_스케줄_해제.bat
  echo  - log       : CODEX_VIDEO_DESK\TEMP\panel\panel_logs\library_backup_scheduled.log
)
pause
