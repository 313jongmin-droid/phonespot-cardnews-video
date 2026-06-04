@echo off
chcp 65001 > nul
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo  PhoneSpot News Shorts - CODEX HYPERFRAMES TEST
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
    echo [ERROR] No number entered.
    goto :hold
)

set "SLUG="
for /f "delims=" %%S in ('python scripts\get_slug.py %NUM%') do set "SLUG=%%S"
echo  [DEBUG] NUM=%NUM%  SLUG=!SLUG!

if "!SLUG!"=="" (
    echo [ERROR] Invalid number: %NUM%.
    goto :hold
)

where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js not found.
    goto :hold
)
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found.
    goto :hold
)

echo.
echo ----- Step 1/6: prepare shared assets -----
python scripts\build_script.py !SLUG!
if errorlevel 1 goto :fail
python scripts\copy_assets.py !SLUG!
if errorlevel 1 goto :fail

echo.
echo ----- Step 2/6: edge-tts install -----
python -m pip install --quiet --upgrade edge-tts
if errorlevel 1 goto :fail

echo.
echo ----- Step 3/6: Generate TTS -----
python scripts\generate_tts.py
if errorlevel 1 goto :fail

echo.
echo ----- Step 4/6: Generate HyperFrames HTML -----
python scripts\prepare_hyperframes.py !SLUG!
if errorlevel 1 goto :fail

echo.
echo ----- Step 5/6: HyperFrames doctor -----
call npx hyperframes doctor
if errorlevel 1 (
    echo [WARN] hyperframes doctor reported an issue. Trying render anyway.
)

echo.
echo ----- Step 6/6: HyperFrames render -----
if not exist out_codex mkdir out_codex
for /f %%D in ('python scripts\today.py') do set "DATE=%%D"
if "%DATE%"=="" set "DATE=nodate"
set "OUTFILE=out_codex\!SLUG!_%DATE%_codex_hyperframes.mp4"
if exist "%OUTFILE%" (
    set "OUTFILE=out_codex\!SLUG!_%DATE%_codex_hyperframes_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%.mp4"
    set "OUTFILE=!OUTFILE: =0!"
)
pushd hyperframes_codex
call npx hyperframes render index.html --output "..\!OUTFILE!" --fps 30 --quality high
set "HF_EXIT=%ERRORLEVEL%"
popd
if not "%HF_EXIT%"=="0" goto :fail

echo.
echo ----- Publish: copy to upload_codex/ -----
if not exist "..\upload_codex" mkdir "..\upload_codex"
set "PUBNAME=%DATE%_!SLUG!_codex_hyperframes"
copy /Y "!OUTFILE!" "..\upload_codex\!PUBNAME!.mp4" >nul
if exist "..\cardnews\output\!SLUG!\captions.md" copy /Y "..\cardnews\output\!SLUG!\captions.md" "..\upload_codex\!PUBNAME!.md" >nul
echo  [OK] ..\upload_codex\!PUBNAME!.mp4

echo.
echo ============================================================
echo  DONE. Result: !OUTFILE!
echo ============================================================
goto :hold

:fail
echo [ERROR] Codex HyperFrames build failed.

:hold
echo.
echo Press any key to close this window...
pause >nul
