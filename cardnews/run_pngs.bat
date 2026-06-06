@echo off
cd /d %~dp0
set PYTHONIOENCODING=utf-8
set "ERR=0"
if exist "%~dp0..\.phonespot_runtime\Scripts\python.exe" (
    set "PATH=%~dp0..\.phonespot_runtime\Scripts;%PATH%"
)

if "%~1"=="" goto select_mode
goto arg_mode

:select_mode
rem === Select mode: console output for interactive pick ===
where python >nul 2>&1
if errorlevel 1 goto select_py
python -u scripts\run_windows.py
set "ERR=%ERRORLEVEL%"
goto select_loop_prompt

:select_py
where py >nul 2>&1
if errorlevel 1 goto python_missing
py -3 -u scripts\run_windows.py
set "ERR=%ERRORLEVEL%"
goto select_loop_prompt

:select_loop_prompt
if not "%ERR%"=="0" exit /b %ERR%
echo.
set "AGAIN="
set /p AGAIN="More work? Press 'y' to select another, any other key to exit: "
if /i "%AGAIN%"=="y" goto select_mode
exit /b 0

:arg_mode
rem === Arg mode: log to file for batch/automation ===
echo === start %date% %time% > run_log.txt
echo. >> run_log.txt
echo [probe] where py: >> run_log.txt
where py >> run_log.txt 2>&1
echo. >> run_log.txt

where python >nul 2>&1
if errorlevel 1 goto try_py

echo [using python] >> run_log.txt
python -u scripts\run_windows.py %* >> run_log.txt 2>&1
set "ERR=%ERRORLEVEL%"
goto end

:try_py
where py >nul 2>&1
if errorlevel 1 goto python_missing_log
echo [using py -3] >> run_log.txt
py -3 -u scripts\run_windows.py %* >> run_log.txt 2>&1
set "ERR=%ERRORLEVEL%"
goto end

:python_missing_log
echo [error] python not found >> run_log.txt
set "ERR=9009"
goto end

:python_missing
echo [error] python not found
exit /b 9009

:end
echo. >> run_log.txt
echo. >> run_log.txt
echo === done %date% %time% >> run_log.txt
exit /b %ERR%
