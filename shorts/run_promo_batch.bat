@echo off
chcp 65001 > nul
cd /d "%~dp0"
setlocal enabledelayedexpansion
REM usage: run_promo_batch.bat [preset]   (no arg = per-script preset)
set "FORCE=%1"

where node >nul 2>nul || ( echo [ERROR] Node.js not found & goto :hold )
where python >nul 2>nul || ( echo [ERROR] Python not found & goto :hold )
if not exist node_modules ( call npm install --no-audit --no-fund )
if not exist out\promo mkdir out\promo
if not exist public mkdir public

set "CNT=0"
for /f "tokens=1-4 delims=|" %%a in ('python scripts\promo_get.py') do (
  set "NN=%%a" & set "SLUG=%%b" & set "PRESET=%%c" & set "FILE=%%d"
  if not "%FORCE%"=="" set "PRESET=%FORCE%"
  set "COMPID=Promo-!PRESET!"
  echo.
  echo ===== !NN! !SLUG! [!PRESET!] =====
  python scripts\promo_md2json.py !NN!
  copy /Y "!FILE!" "public\shorts_script.json" >nul
  python scripts\promo_merge_brand.py
  python scripts\promo_pick_music.py !PRESET! !NN!
  call :uniq "out\promo\!NN!_!SLUG!_!PRESET!"
  call npx remotion render src/index.ts !COMPID! "!OUTFILE!" --concurrency=2 --pixel-format yuv420p --crf 18
  python scripts\promo_manifest.py "!OUTFILE!" !NN! !SLUG! !PRESET!
  python scripts\promo_uploadkit.py !NN! "!OUTFILE!"
  set /a CNT+=1
)
echo.
echo  done. rendered !CNT! -^> out\promo\
goto :hold
:uniq
set "BASE=%~1"
set "OUTFILE=!BASE!.mp4"
set /a K=1
:uniqloop
if exist "!OUTFILE!" ( set "OUTFILE=!BASE!_!K!.mp4" & set /a K+=1 & goto uniqloop )
exit /b
:hold
endlocal
pause
