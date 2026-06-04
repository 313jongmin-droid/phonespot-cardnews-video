@echo off
cd /d %~dp0
set PYTHONIOENCODING=utf-8

if "%~1"=="" goto select_mode
goto arg_mode

:select_mode
rem === Select mode: console output for interactive pick ===
where py >nul 2>&1
if errorlevel 1 goto select_direct
py -3 -u scripts\run_windows.py
goto select_loop_prompt

:select_direct
for %%P in ("%LOCALAPPDATA%\Programs\Python\Python313\python.exe" "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" "C:\Python313\python.exe" "C:\Python312\python.exe" "C:\Python311\python.exe") do (
    if exist %%P (
        %%P -u scripts\run_windows.py
        goto select_loop_prompt
    )
)
echo [error] python not found

:select_loop_prompt
echo.
set "AGAIN="
set /p AGAIN="More work? Press 'y' to select another, any other key to exit: "
if /i "%AGAIN%"=="y" goto select_mode
exit /b

:arg_mode
rem === Arg mode: log to file for batch/automation ===
echo === start %date% %time% > run_log.txt
echo. >> run_log.txt
echo [probe] where py: >> run_log.txt
where py >> run_log.txt 2>&1
echo. >> run_log.txt

where py >nul 2>&1
if errorlevel 1 goto try_direct

echo [using py] >> run_log.txt
py -3 -u scripts\run_windows.py %* >> run_log.txt 2>&1
goto end

:try_direct
for %%P in ("%LOCALAPPDATA%\Programs\Python\Python313\python.exe" "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" "C:\Python313\python.exe" "C:\Python312\python.exe" "C:\Python311\python.exe") do (
    if exist %%P (
        echo [using %%P] >> run_log.txt
        %%P -u scripts\run_windows.py %* >> run_log.txt 2>&1
        goto end
    )
)

echo [error] python not found >> run_log.txt

:end
echo. >> run_log.txt
echo. >> run_log.txt
echo === done %date% %time% >> run_log.txt
exit /b
