@echo off
setlocal
chcp 65001 >nul
title PhoneSpot - Embedding Setup (run once per PC)

rem Installs the free local embedding engine into the SAME python the panel uses.
rem The panel (start_hidden.ps1) prefers .phonespot_runtime\Scripts\python.exe,
rem so we install there first. Otherwise it falls back to system python.

pushd "%~dp0" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Cannot enter shorts folder: %~dp0
  pause
  exit /b 1
)

rem ---- prefer the panel runtime venv python (matches start_hidden.ps1) ----
set "PY="
set "RUNTIME=%~dp0..\.phonespot_runtime\Scripts\python.exe"
if exist "%RUNTIME%" set "PY=%RUNTIME%"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY ( where py >nul 2>nul && set "PY=py" )
if not defined PY ( where python3 >nul 2>nul && set "PY=python3" )
if not defined PY (
  echo [ERROR] Python not found. Install Python and run again.
  popd
  pause
  exit /b 1
)
echo Using Python: %PY%
echo (this MUST be the same python the panel runs - the runtime venv if present)

echo.
echo ===== 1/4: install fastembed / numpy / pillow / socksio =====
rem pillow is needed by the CLIP image embedder to decode PNG/JPG.
"%PY%" -m pip install --upgrade fastembed numpy pillow socksio
if errorlevel 1 (
  echo [WARN] normal install failed - retry with --user
  "%PY%" -m pip install --user --upgrade fastembed numpy pillow socksio
)

echo.
echo ===== 2/4: text model download + self-test =====
echo (first run downloads the text model, may take 1-2 minutes)
"%PY%" scripts\codex_illust_embed.py selftest

echo.
echo ===== 3/4: CLIP image model download + self-test =====
echo (downloads jina-clip-v1 for matching by PICTURE CONTENT, ~1GB total, one time)
"%PY%" scripts\codex_image_embed.py selftest

echo.
echo ===== 4/4: final check =====
set "TEXT_OK=1"
set "IMG_OK=1"
"%PY%" scripts\codex_illust_embed.py check
if errorlevel 1 set "TEXT_OK=0"
"%PY%" scripts\codex_image_embed.py check
if errorlevel 1 set "IMG_OK=0"
echo.
if "%TEXT_OK%"=="1" (
  echo [RESULT] Text embedding ENABLED ^(TRUE^).
) else (
  echo [RESULT] Text embedding NOT available ^(FALSE^) - lexical fallback.
)
if "%IMG_OK%"=="1" (
  echo [RESULT] Image-content matching ENABLED ^(TRUE^).
  echo          Button 2 import review + reuse-by-picture now active.
) else (
  echo [RESULT] Image-content matching NOT available ^(FALSE^).
  echo          - Check internet/proxy/pillow, then run this file again.
  echo          - Import still works via filename-order fallback.
)

popd
echo.
pause
