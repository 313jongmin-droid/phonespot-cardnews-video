@echo off
setlocal enabledelayedexpansion
rem Cover-only re-render for one slug (no full video render).
rem Copies the slug built script to public then renders the Cover still.
rem usage: run_cover.bat <slug>
set "SLUG=%~1"
if "%SLUG%"=="" ( echo [ERROR] usage: run_cover.bat ^<slug^> & exit /b 2 )
cd /d "%~dp0"
set "SRC=..\cardnews\output\%SLUG%\shorts_script.json"
if not exist "%SRC%" ( echo [ERROR] built script not found: %SRC% ^(render the video once first^) & exit /b 3 )
copy /Y "%SRC%" "public\shorts_script.json" >nul
set "RESULTDIR=..\CODEX_VIDEO_DESK\RESULTS\%SLUG%_cover"
if not exist "%RESULTDIR%" mkdir "%RESULTDIR%"
set "COVERFILE=%RESULTDIR%\%SLUG%_cover.jpg"
echo ----- Cover only: %SLUG% -----
call node scripts\render_cover.mjs "%COVERFILE%" Cover
if exist "%COVERFILE%" ( echo  Cover OK: %COVERFILE% & exit /b 0 ) else ( echo  [ERROR] cover not generated & exit /b 1 )
