@echo off
cd /d %~dp0
set PYTHONIOENCODING=utf-8

if not exist _state mkdir _state

echo === telegram listener start %date% %time% > _state\listener_log.txt

where py >nul 2>&1
if errorlevel 1 goto try_direct

..\.phonespot_runtime\Scripts\python.exe -u scripts\telegram_listener.py >> _state\listener_log.txt 2>&1
goto end

:try_direct
for %%P in ("%LOCALAPPDATA%\Programs\Python\Python313\python.exe" "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "%LOCALAPPDATA%\Programs\Python\Python310\python.exe") do (
    if exist %%P (
        %%P -u scripts\telegram_listener.py >> _state\listener_log.txt 2>&1
        goto end
    )
)

echo [error] python not found >> _state\listener_log.txt

:end
echo === listener stopped %date% %time% >> _state\listener_log.txt