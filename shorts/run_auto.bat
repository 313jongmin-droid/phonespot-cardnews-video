@echo off
chcp 65001 > nul
cd /d "%~dp0"
setlocal enabledelayedexpansion

REM 자동 새벽 빌드 파이프라인 (윈도우 스케줄러용)
REM 1) auto_polish.py : 새 [OK] 슬러그 자동 매핑 + shorts_script.json 박기
REM 2) run_B_batch 흐름 (all): 모든 [OK] 슬러그 빌드 + upload/ 복사
REM 3) (옵션) 텔레그램 알림

echo.
echo ============================================================
echo  PhoneSpot AUTO Pipeline  %DATE% %TIME%
echo ============================================================

REM Env check
where node >nul 2>nul
if errorlevel 1 (echo [ERROR] Node.js not found & exit /b 1)
where python >nul 2>nul
if errorlevel 1 (echo [ERROR] Python not found & exit /b 1)
if not exist node_modules call npm install --no-audit --no-fund --silent
python -m pip install --quiet --upgrade edge-tts

REM Date
for /f %%D in ('python scripts\today.py') do set "DATE=%%D"
if "%DATE%"=="" set "DATE=nodate"
if not exist out mkdir out

REM ===== Step 1: auto_polish =====
echo.
echo ----- Step 1/2: auto_polish (new slugs) -----
python scripts\auto_polish.py

REM ===== Step 1.5: validate (errors 만 빌드 차단) =====
echo.
echo ----- Step 1.5/2: validate shorts_script.json -----
python scripts\validate_polish.py
if errorlevel 2 (
    echo [ERROR] validate_polish: critical errors. Build skipped.
    if exist scripts\notify.py python scripts\notify.py "[FAIL] validate errors. Build skipped."
    exit /b 2
)

REM ===== Step 2: build all [OK] slugs =====
echo.
echo ----- Step 2/2: build all [OK] slugs -----
set "NUMS="
for /f "tokens=1,*" %%a in ('python scripts\list_slugs.py') do (
    echo %%b | findstr /C:"[OK]" >nul && set "NUMS=!NUMS! %%a"
)
set "NUMS=!NUMS:.= !"

set "OK_COUNT=0"
set "FAIL_COUNT=0"
set "FAIL_LIST="

for %%N in (!NUMS!) do (
    call :process_one %%N
)

echo.
echo.
echo ----- Step 3/3: telegram report -----
python scripts\report_polish.py

echo ============================================================
echo  AUTO BUILD DONE.  OK=!OK_COUNT!  FAIL=!FAIL_COUNT!
if defined FAIL_LIST echo  Failed: !FAIL_LIST!
echo ============================================================

REM 텔레그램 알림 (옵션, scripts/notify.py 가 있으면 실행)
if exist scripts\notify.py (
    python scripts\notify.py "AUTO BUILD %DATE% : OK=!OK_COUNT! FAIL=!FAIL_COUNT!"
)

exit /b 0

:process_one
set "CUR=%~1"
set "SLUG="
for /f "delims=" %%S in ('python scripts\get_slug.py %CUR%') do set "SLUG=%%S"
echo.
echo --- [%CUR%] !SLUG! ---
if "!SLUG!"=="" (
    set /a FAIL_COUNT+=1
    exit /b 0
)

REM 이미 오늘 빌드된 슬러그 skip (선택)
if exist "..\upload\%DATE%_!SLUG!.mp4" (
    echo  [SKIP] already built today
    exit /b 0
)

python scripts\build_script.py "!SLUG!"
if errorlevel 1 goto :proc_fail
python scripts\copy_assets.py "!SLUG!"
if errorlevel 1 goto :proc_fail
python scripts\generate_tts.py
if errorlevel 1 goto :proc_fail

set "OUTFILE="
for /f "delims=" %%F in ('python scripts\next_outfile.py "!SLUG!" %DATE% casual') do set "OUTFILE=out\%%F"
if "!OUTFILE!"=="" set "OUTFILE=out\!SLUG!_%DATE%_casual.mp4"

call npx remotion render src/index.ts CasualShort "!OUTFILE!" --concurrency=2 --pixel-format yuv420p --crf 18
if errorlevel 1 goto :proc_fail

if not exist "..\upload" mkdir "..\upload"
set "PUBNAME=%DATE%_!SLUG!"
copy /Y "!OUTFILE!" "..\upload\!PUBNAME!.mp4" >nul
if exist "..\cardnews\output\!SLUG!\captions.md" copy /Y "..\cardnews\output\!SLUG!\captions.md" "..\upload\!PUBNAME!.md" >nul
echo  [OK] !PUBNAME!.mp4 + .md
set /a OK_COUNT+=1
exit /b 0

:proc_fail
echo  [FAIL] !SLUG!
set /a FAIL_COUNT+=1
set "FAIL_LIST=!FAIL_LIST! %CUR%(!SLUG!)"
exit /b 0
