@echo off
chcp 65001 > nul
cd /d "%~dp0"
setlocal enabledelayedexpansion

set TRACK=casual
set COMPID=CasualShort

echo.
echo ============================================================
echo  PhoneSpot News Shorts  -  TRACK: casual
echo ============================================================
echo.
echo Select a news folder by number  (#   date        flag  slug):
echo ------------------------------------------------------------
python scripts\list_slugs.py
echo ------------------------------------------------------------
echo.
set "NUM="
set /p NUM=Enter number: 

if "%NUM%"=="" (
    echo [ERROR] No number entered. Aborting.
    goto :hold
)

REM 매핑: list_slugs.py 와 동일한 정렬 기준으로 N번째 슬러그명 가져옴
set "SLUG="
for /f "delims=" %%S in ('python scripts\get_slug.py %NUM%') do set "SLUG=%%S"
echo  [DEBUG] NUM=%NUM%  SLUG=!SLUG!

if "!SLUG!"=="" (
    echo [ERROR] Invalid number: %NUM%. No folder mapped.
    goto :hold
)
if not exist "..\cardnews\output\!SLUG!" (
    echo [ERROR] Folder not found: ..\cardnews\output\!SLUG!
    goto :hold
)

echo.
echo  Track: casual   Slug: !SLUG!
echo.

where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install LTS: https://nodejs.org/en/download
    goto :hold
)
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install 3.10+: https://www.python.org/downloads/
    goto :hold
)

echo ----- Step 1/5: npm install -----
if not exist node_modules (
    call npm install --no-audit --no-fund
    if errorlevel 1 (
        echo [ERROR] npm install failed.
        goto :hold
    )
) else (
    echo  already installed - skip
)

echo.
echo ----- Step 2/5: edge-tts install -----
python -m pip install --quiet --upgrade edge-tts
if errorlevel 1 (
    echo [ERROR] edge-tts install failed.
    goto :hold
)
echo [OK] edge-tts ready

echo.
echo ----- Step 3/5: Build script + copy assets -----
python scripts\build_script.py !SLUG!
if errorlevel 1 (
    echo [ERROR] build_script failed for slug: !SLUG!
    goto :hold
)
python scripts\copy_assets.py !SLUG!
if errorlevel 1 (
    echo [ERROR] copy_assets failed for slug: !SLUG!
    goto :hold
)

echo.
echo ----- Step 4/5: Generate TTS -----
python scripts\generate_tts.py
if errorlevel 1 (
    echo [ERROR] TTS generation failed.
    goto :hold
)

echo.
echo ----- Step 5/5: Remotion render -----
if not exist out mkdir out
for /f %%D in ('python scripts\today.py') do set "DATE=%%D"
if "%DATE%"=="" set "DATE=nodate"
set "OUTFILE="
for /f "delims=" %%F in ('python scripts\next_outfile.py !SLUG! %DATE% casual') do set "OUTFILE=out\%%F"
if "%OUTFILE%"=="" set "OUTFILE=out\!SLUG!_%DATE%_casual.mp4"
echo  Output: %OUTFILE%
call npx remotion render src/index.ts CasualShort "%OUTFILE%" --concurrency=2 --pixel-format yuv420p --crf 18
if errorlevel 1 (
    echo [ERROR] Remotion render failed.
    goto :hold
)


echo.
echo ----- Publish: copy to upload/ -----
if not exist "..\upload" mkdir "..\upload"
set "PUBNAME=%DATE%_!SLUG!"
copy /Y "%OUTFILE%" "..\upload\!PUBNAME!.mp4" >nul
if exist "..\cardnews\output\!SLUG!\captions.md" (
    copy /Y "..\cardnews\output\!SLUG!\captions.md" "..\upload\!PUBNAME!.md" >nul
    echo  [OK] ..\upload\!PUBNAME!.mp4 + .md
) else (
    echo  [OK] ..\upload\!PUBNAME!.mp4 (captions.md missing)
)

echo.
echo ============================================================
echo  DONE.  Result: %OUTFILE%
echo ============================================================
echo.
goto :hold

:hold
