@echo off
setlocal enabledelayedexpansion
rem Cover-only re-render (all 3 color variants) for one slug. No full video render.
rem usage: run_cover.bat <slug>
set "SLUG=%~1"
if "%SLUG%"=="" ( echo [ERROR] usage: run_cover.bat ^<slug^> & exit /b 2 )
cd /d "%~dp0"
set "SRC=..\cardnews\output\%SLUG%\shorts_script.json"
if not exist "%SRC%" ( echo [ERROR] built script not found: %SRC% ^(render the video once first^) & exit /b 3 )
copy /Y "%SRC%" "public\shorts_script.json" >nul
set "RESULTDIR=..\CODEX_VIDEO_DESK\RESULTS\%SLUG%_cover"
if not exist "%RESULTDIR%" mkdir "%RESULTDIR%"
set "MADE=0"
for %%V in (0 1 2) do (
  set "COVERFILE=%RESULTDIR%\%SLUG%_cover_v%%V.jpg"
  echo ----- Cover variant %%V : %SLUG% -----
  call node scripts\render_cover.mjs "!COVERFILE!" Cover %%V
  if exist "!COVERFILE!" ( echo  OK v%%V: !COVERFILE! & set "MADE=1" )
)
if "!MADE!"=="1" ( echo  Cover done ^(3 variants^): %RESULTDIR% & exit /b 0 ) else ( echo  [ERROR] no cover generated & exit /b 1 )
