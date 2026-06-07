@echo off
rem ============================================================
rem  PhoneSpot panel auto-update (receiver PCs, opt-in)
rem  - git pull --ff-only only (fast). Full deps update stays in
rem    the "system update" button (codex_github_update.py).
rem  - All output goes to a log file. ALWAYS exits 0 so it can
rem    never block panel startup.
rem ============================================================
setlocal enabledelayedexpansion
set "HERE=%~dp0"
for %%I in ("%HERE%..\..") do set "ROOT=%%~fI"
set "LOGDIR=%HERE%..\TEMP\panel\panel_logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>&1
set "LOG=%LOGDIR%\auto_update.log"

if not exist "%ROOT%\.git" (
  >>"%LOG%" echo [%date% %time%] [skip] not a git repo: %ROOT%
  exit /b 0
)

set "GIT=git"
where git >nul 2>&1
if errorlevel 1 (
  if exist "C:\Program Files\Git\cmd\git.exe" (
    set "GIT=C:\Program Files\Git\cmd\git.exe"
  ) else (
    >>"%LOG%" echo [%date% %time%] [skip] git not found
    exit /b 0
  )
)

>>"%LOG%" echo.
>>"%LOG%" echo [%date% %time%] auto-update: git pull --ff-only in "%ROOT%"
"%GIT%" -C "%ROOT%" pull --ff-only >>"%LOG%" 2>&1
>>"%LOG%" echo [exit] !errorlevel!
exit /b 0
