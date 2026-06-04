@echo off
cd /d %~dp0\..
set PYTHONIOENCODING=utf-8

where py >nul 2>&1
if errorlevel 1 goto try_direct

py -3 -m pip install --quiet flask 2>nul
py -3 -u webui\app.py
goto end

:try_direct
for %%P in ("%LOCALAPPDATA%\Programs\Python\Python313\python.exe" "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" "C:\Python313\python.exe" "C:\Python312\python.exe" "C:\Python311\python.exe") do (
    if exist %%P (
        %%P -m pip install --quiet flask 2>nul
        %%P -u webui\app.py
        goto end
    )
)

echo [error] python not found

:end
pause
exit /b
