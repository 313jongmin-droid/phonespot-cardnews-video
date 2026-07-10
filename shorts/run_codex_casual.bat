@echo off
chcp 65001 > nul
cd /d "%~dp0"
setlocal enabledelayedexpansion
if exist "%~dp0..\.phonespot_runtime\Scripts\python.exe" (
    for %%I in ("%~dp0..\.phonespot_runtime\Scripts") do set "PATH=%%~fI;%PATH%"
)
set "EXITCODE=0"
set "SLUG=%~1"
if not "!SLUG!"=="" goto :slug_selected

echo.
echo ============================================================
echo  PhoneSpot News Shorts - CODEX REMOTION QUALITY
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
    goto :fail
)

set "SLUG="
for /f "delims=" %%S in ('python scripts\get_slug.py %NUM%') do set "SLUG=%%S"
echo  [DEBUG] NUM=%NUM%  SLUG=!SLUG!

if "!SLUG!"=="" (
    echo [ERROR] Invalid number: %NUM%.
    goto :fail
)

:slug_selected
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js not found.
    goto :fail
)
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found.
    goto :fail
)

echo.
echo ----- Step 1/7: npm install -----
if not exist node_modules (
    call npm install --no-audit --no-fund
    if errorlevel 1 goto :fail
) else (
    echo  already installed - skip
)

echo.
echo ----- Step 2/7: edge-tts check -----
python -c "import edge_tts" >nul 2>nul
if errorlevel 1 (
    echo  edge-tts missing - existing matching audio can still be reused
) else (
    echo  already installed - skip
)

echo.
rem ----- real-photo match threshold: TEST default 0.5 (headline boosts photo scores ~0.5-0.6;
rem        0.6 blocked relevant chip photos. 'photo >= best_ill' rule still guards weak photos) -----
if "%PHONESPOT_PHOTO_MIN%"=="" set "PHONESPOT_PHOTO_MIN=0.5"
rem ----- CLIP content-gate (cross-modal text<->image, low scale 0.2-0.3): 0.24 lets on-topic art pass, wrong out -----
if "%PHONESPOT_IMG_MATCH_MIN%"=="" set "PHONESPOT_IMG_MATCH_MIN=0.24"
echo ----- Step 3/7: Build script + copy assets -----
python scripts\build_script.py !SLUG!
if errorlevel 1 goto :fail
python scripts\codex_enhance_script.py !SLUG!
if errorlevel 1 goto :fail
python scripts\codex_photo_tag.py
python scripts\codex_semantic_visual_match.py !SLUG!
if errorlevel 1 goto :fail
python scripts\codex_unique_illustration_guard.py !SLUG!
if errorlevel 1 goto :fail
python scripts\codex_apply_uploaded_illustrations.py !SLUG!
if errorlevel 1 goto :fail
python scripts\codex_illustration_scout.py !SLUG!
if errorlevel 1 goto :fail
python scripts\codex_refresh_workbench.py !SLUG!
if errorlevel 1 goto :fail
python scripts\validate_codex_korean.py !SLUG!
if errorlevel 1 goto :fail
python scripts\validate_caption_compiler_v2.py !SLUG!
if errorlevel 1 goto :fail
python scripts\sync_codex_illustrations.py
if errorlevel 1 goto :fail
python scripts\copy_assets.py !SLUG!
if errorlevel 1 goto :fail
python scripts\validate_effective_script.py !SLUG!
if errorlevel 1 goto :fail

echo.
echo ----- Step 4/7: Generate normalized TTS -----
if "%PHONESPOT_TTS_RATE%"=="" set "PHONESPOT_TTS_RATE=+42%%"
if "%PHONESPOT_TTS_LOUDNORM%"=="" set "PHONESPOT_TTS_LOUDNORM=1"
python scripts\generate_tts.py
if errorlevel 1 goto :fail
python scripts\verify_tts_timing.py --allow-char-fallback
if errorlevel 1 goto :fail

echo.
echo ----- Step 5/7: Remotion raw render -----
if "%PHONESPOT_LOCAL_RUNTIME%"=="" set "PHONESPOT_LOCAL_RUNTIME=%LOCALAPPDATA%\PhoneSpotCodexVideo"
set "LOCAL_RAW=%PHONESPOT_LOCAL_RUNTIME%\temp\_raw"
if not exist "!LOCAL_RAW!" mkdir "!LOCAL_RAW!"
if not exist "..\CODEX_VIDEO_DESK\RESULTS" mkdir "..\CODEX_VIDEO_DESK\RESULTS"
for /f %%D in ('python scripts\today.py') do set "DATE=%%D"
if "%DATE%"=="" set "DATE=nodate"
set "RESULTKEY=!DATE!_!SLUG!_codex_remotion"
set "RESULTDIR=..\CODEX_VIDEO_DESK\RESULTS\!RESULTKEY!"
if exist "!RESULTDIR!" (
    set "RESULTKEY=!RESULTKEY!_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
    set "RESULTKEY=!RESULTKEY: =0!"
    set "RESULTDIR=..\CODEX_VIDEO_DESK\RESULTS\!RESULTKEY!"
)
if not exist "!RESULTDIR!" mkdir "!RESULTDIR!"
set "OUTFILE=!RESULTDIR!\!RESULTKEY!.mp4"
set "RAWFILE=!LOCAL_RAW!\!SLUG!_!DATE!_codex_remotion_raw.mp4"
if exist "!RAWFILE!" del /q "!RAWFILE!" >nul 2>nul
echo  Raw: !RAWFILE!
set "RENDERLOG=!RESULTDIR!\remotion_raw_render.log"
echo  Log: !RENDERLOG!
if "%PHONESPOT_RENDER_CONCURRENCY%"=="" set "PHONESPOT_RENDER_CONCURRENCY=50%%"
if "%PHONESPOT_RAW_CRF%"=="" set "PHONESPOT_RAW_CRF=23"
if "%PHONESPOT_RAW_PRESET%"=="" set "PHONESPOT_RAW_PRESET=veryfast"
rem GPU(옵트인): blur/box-shadow/gradient 많은 컴포지션 가속. 기본 미설정=기존 CPU 동작.
rem 테스트:  set PHONESPOT_GL=angle  (필요시 set PHONESPOT_CHROME_MODE=chrome-for-testing)
set "GLARGS="
if not "%PHONESPOT_GL%"=="" set "GLARGS=--gl=%PHONESPOT_GL%"
if not "%PHONESPOT_CHROME_MODE%"=="" set "GLARGS=!GLARGS! --chrome-mode=%PHONESPOT_CHROME_MODE%"
echo  Concurrency: !PHONESPOT_RENDER_CONCURRENCY!  (raw crf=!PHONESPOT_RAW_CRF! preset=!PHONESPOT_RAW_PRESET!)  GPU: !GLARGS!
rem Fast path: reuse webpack bundle across renders (#3) + tunable concurrency (#1)
rem + cheap intermediate encode (#2; Step 6 finalize is the quality gate).
call node scripts\render_remotion_fast.mjs CasualShort "!RAWFILE!" > "!RENDERLOG!" 2>&1
if errorlevel 1 (
    echo  [WARN] fast render path failed - falling back to Remotion CLI. See log.
    call npx remotion render src/index.ts CasualShort "!RAWFILE!" --pixel-format=yuv420p --crf=!PHONESPOT_RAW_CRF! --x264-preset=!PHONESPOT_RAW_PRESET! !GLARGS! >> "!RENDERLOG!" 2>&1
)
if errorlevel 1 (
    echo [ERROR] Remotion raw render command failed. See:
    echo !RENDERLOG!
    type "!RENDERLOG!"
    goto :fail
)
if not exist "!RAWFILE!" (
    echo [ERROR] Remotion finished but raw file was not created:
    echo !RAWFILE!
    echo [ERROR] Raw render log:
    type "!RENDERLOG!"
    goto :fail
)
for %%A in ("!RAWFILE!") do set "RAWSIZE=%%~zA"
if "!RAWSIZE!"=="0" (
    echo [ERROR] Remotion raw file is 0 bytes:
    echo !RAWFILE!
    echo [ERROR] Raw render log:
    type "!RENDERLOG!"
    goto :fail
)
echo  Raw OK: !RAWSIZE! bytes

echo.
echo ----- Step 6/7: Finalize SNS MP4 -----
echo  Output: !OUTFILE!
python scripts\finalize_sns_video.py "!RAWFILE!" "!OUTFILE!"
if errorlevel 1 goto :fail
del /q "!RAWFILE!" >nul 2>nul

rem Keep source, manual override, and the exact rendered script next to the MP4.
if exist "..\cardnews\output\!SLUG!\shorts_script.json" copy /Y "..\cardnews\output\!SLUG!\shorts_script.json" "!RESULTDIR!\shorts_script.source.json" >nul 2>nul
if exist "public\shorts_script.json" copy /Y "public\shorts_script.json" "!RESULTDIR!\shorts_script.effective.json" >nul 2>nul
if exist "..\CODEX_VIDEO_DESK\CHUNK_OVERRIDES\!SLUG!.json" copy /Y "..\CODEX_VIDEO_DESK\CHUNK_OVERRIDES\!SLUG!.json" "!RESULTDIR!\chunk_override.json" >nul 2>nul
if exist "..\cardnews\output\!SLUG!\captions.md" copy /Y "..\cardnews\output\!SLUG!\captions.md" "!RESULTDIR!\" >nul 2>nul

rem ----- Cover image (9:16 still) - best effort, reuses cached bundle -----
echo.
echo ----- Cover image (9:16) -----
set "COVERFILE=!RESULTDIR!\!RESULTKEY!_cover.jpg"
call node scripts\render_cover.mjs "!COVERFILE!" Cover >> "!RENDERLOG!" 2>&1
if exist "!COVERFILE!" (
    echo  Cover OK: !COVERFILE!
) else (
    echo  [WARN] cover image not generated - see !RENDERLOG!
)

echo.
echo ----- Step 7/7: Quality check + result package -----
python scripts\verify_video_quality.py "!OUTFILE!"
if errorlevel 1 goto :fail
python scripts\publish_codex_package.py "!OUTFILE!" "!SLUG!" "!DATE!"
if errorlevel 1 (
    echo  [WARN] Result metadata generation failed. Final MP4 remains available.
)
echo.
echo ============================================================
echo  DONE. Result folder: !RESULTDIR!
echo ============================================================
goto :hold
:fail
set "EXITCODE=1"
echo.
echo [ERROR] Codex Remotion build failed.

:hold
echo.
if "!PHONESPOT_NO_PAUSE!"=="1" goto :end
echo Press any key to close this window...
pause >nul
:end
exit /b !EXITCODE!
