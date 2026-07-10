@echo off
chcp 65001 > nul
cd /d "%~dp0"
setlocal enabledelayedexpansion

set TRACK=casual
set COMPID=CasualShort

echo.
echo ============================================================
echo  PhoneSpot News Shorts - BATCH (TRACK: casual)
echo ============================================================
echo.
python scripts\list_slugs.py
echo.
echo  - "all" : [OK] flag slugs all
echo  - "1 8 13" : space separated numbers
echo  - "12,15,20" : comma separated also OK
echo.
set "NUMS="
set /p NUMS=Enter numbers (or all): 
if "%NUMS%"=="" goto :err_input

REM Normalize: comma to space, dot to space
set "NUMS=%NUMS:,= %"
set "NUMS=%NUMS:.= %"

REM all option
if /I "%NUMS%"=="all" (
    set "TMPNUMS="
    for /f "tokens=1,*" %%a in ('python scripts\list_slugs.py') do (
        echo %%b | findstr /C:"[OK]" >nul && set "TMPNUMS=!TMPNUMS! %%a"
    )
    set "NUMS=!TMPNUMS!"
    set "NUMS=!NUMS:.= !"
)

echo.
echo  Build queue: !NUMS!
echo.

REM Environment check (once)
where node >nul 2>nul
if errorlevel 1 (echo [ERROR] Node.js not found & goto :hold)
where python >nul 2>nul
if errorlevel 1 (echo [ERROR] Python not found & goto :hold)
if not exist node_modules (
    echo [INFO] npm install ...
    call npm install --no-audit --no-fund
)
echo [INFO] edge-tts check ...
python -m pip install --quiet --upgrade edge-tts

REM Date (once)
for /f %%D in ('python scripts\today.py') do set "DATE=%%D"
if "%DATE%"=="" set "DATE=nodate"
if not exist out mkdir out

set "OK_COUNT=0"
set "FAIL_COUNT=0"
set "FAIL_LIST="

REM Iterate slug numbers (call subroutine — for-loop variable not needed inside)
for %%N in (%NUMS%) do (
    call :process_one %%N
)

echo.
echo ============================================================
echo  BATCH DONE.  OK=!OK_COUNT!  FAIL=!FAIL_COUNT!
if defined FAIL_LIST echo  Failed: !FAIL_LIST!
echo ============================================================
goto :hold

REM ============================================================
:process_one
REM %1 = slug number
set "CUR=%~1"
set "SLUG="
for /f "delims=" %%S in ('python scripts\get_slug.py %CUR%') do set "SLUG=%%S"

echo.
echo ============================================================
echo  [%CUR%] !SLUG!
echo ============================================================

if "!SLUG!"=="" (
    echo [SKIP] number %CUR% - mapping failed
    set /a FAIL_COUNT+=1
    set "FAIL_LIST=!FAIL_LIST! %CUR%(map)"
    exit /b 0
)

python scripts\build_script.py "!SLUG!"
if errorlevel 1 goto :build_fail

python scripts\copy_assets.py "!SLUG!"
if errorlevel 1 goto :build_fail

python scripts\generate_tts.py
if errorlevel 1 goto :build_fail

set "OUTFILE="
for /f "delims=" %%F in ('python scripts\next_outfile.py "!SLUG!" %DATE% casual') do set "OUTFILE=out\%%F"
if "!OUTFILE!"=="" set "OUTFILE=out\!SLUG!_%DATE%_casual.mp4"

call npx remotion render src/index.ts CasualShort "!OUTFILE!" --concurrency=2 --pixel-format yuv420p --crf 18
if errorlevel 1 goto :build_fail

REM Publish
if not exist "..\upload" mkdir "..\upload"
set "PUBNAME=%DATE%_!SLUG!"
copy /Y "!OUTFILE!" "..\upload\!PUBNAME!.mp4" >nul
if exist "..\cardnews\output\!SLUG!\captions.md" copy /Y "..\cardnews\output\!SLUG!\captions.md" "..\upload\!PUBNAME!.md" >nul
echo  [OK] !PUBNAME!.mp4 + .md

set /a OK_COUNT+=1
exit /b 0

:build_fail
echo  [FAIL] !SLUG!
set /a FAIL_COUNT+=1
set "FAIL_LIST=!FAIL_LIST! %CUR%(!SLUG!)"
exit /b 0

REM ============================================================
:err_input
echo [ERROR] No input.
goto :hold

:hold
echo.
echo ------------------------------------------------------------
echo  Press any key to close...
pause >nul
endlocal
