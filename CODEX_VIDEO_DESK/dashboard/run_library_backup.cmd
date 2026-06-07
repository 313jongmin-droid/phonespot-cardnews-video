@echo off
rem ============================================================
rem  Run the illustration-library backup once and log output.
rem  Used by the daily Windows scheduled task (and can be run
rem  manually). ALWAYS exits 0.
rem ============================================================
setlocal
set "HERE=%~dp0"
for %%I in ("%HERE%..") do set "DESK=%%~fI"
for %%I in ("%HERE%..\..") do set "ROOT=%%~fI"
set "SCRIPT=%ROOT%\shorts\scripts\codex_library_backup.py"
set "LOGDIR=%DESK%\TEMP\panel\panel_logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>&1
set "LOG=%LOGDIR%\library_backup_scheduled.log"

set "PY=%ROOT%\.phonespot_runtime\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

if not exist "%SCRIPT%" (
  >>"%LOG%" echo [%date% %time%] [skip] script not found: %SCRIPT%
  exit /b 0
)

>>"%LOG%" echo.
>>"%LOG%" echo [%date% %time%] library backup start (py=%PY%)
"%PY%" "%SCRIPT%" >>"%LOG%" 2>&1
>>"%LOG%" echo [exit] %errorlevel%
exit /b 0
