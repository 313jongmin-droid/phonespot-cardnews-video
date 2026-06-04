@echo off
chcp 65001 > nul
cd /d "%~dp0"
setlocal enabledelayedexpansion

where node >nul 2>nul || ( echo [ERROR] Node.js not found: https://nodejs.org/en/download & goto :hold )
where python >nul 2>nul || ( echo [ERROR] Python not found: https://www.python.org/downloads/ & goto :hold )

echo.
echo ============================================================
echo  PHONESPOT PROMO  -  render by number
echo ============================================================
echo.
python scripts\promo_list.py
echo.
set "NUM="
set /p NUM=Render number: 
if "%NUM%"=="" ( echo [ERROR] no number & goto :hold )

set "SLUG="
for /f "tokens=1-4 delims=|" %%a in ('python scripts\promo_get.py %NUM%') do ( set "NN=%%a" & set "SLUG=%%b" & set "PRESET=%%c" & set "FILE=%%d" )
if "%SLUG%"=="" ( echo [ERROR] invalid number: %NUM% & goto :hold )
set "COMPID=Promo-%PRESET%"
echo  pick: %NN% %SLUG% [%PRESET%] -^> %COMPID%
echo.

if not exist node_modules ( call npm install --no-audit --no-fund || ( echo [ERROR] npm install failed & goto :hold ) ) else ( echo  npm: skip )
if not exist public mkdir public
python scripts\promo_md2json.py %NN%
copy /Y "%FILE%" "public\shorts_script.json" >nul || ( echo [ERROR] copy failed & goto :hold )
python scripts\promo_merge_brand.py
python scripts\promo_pick_music.py %PRESET% %NN%
if not exist out\promo mkdir out\promo
set "OUTFILE=out\promo\%NN%_%SLUG%_%PRESET%.mp4"
echo  rendering -^> %OUTFILE%
call npx remotion render src/index.ts %COMPID% "%OUTFILE%" --concurrency=2 --pixel-format yuv420p --crf 18 || ( echo [ERROR] render failed & goto :hold )
echo.
echo  DONE: %OUTFILE%
goto :hold
:hold
endlocal
pause
