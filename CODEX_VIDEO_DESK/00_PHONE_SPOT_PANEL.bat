@echo off
chcp 65001 > nul
setlocal

rem Network-share safe launcher.
rem CMD cannot use UNC paths as the current directory, so pushd maps it to a temp drive.
pushd "%~dp0" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Cannot enter panel folder:
  echo         %~dp0
  echo.
  echo Check network share permission and try again.
  pause
  exit /b 1
)

set "DESK_DIR=%CD%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%DESK_DIR%\dashboard\start_hidden.ps1"
set "ERR=%ERRORLEVEL%"
popd
exit /b %ERR%
