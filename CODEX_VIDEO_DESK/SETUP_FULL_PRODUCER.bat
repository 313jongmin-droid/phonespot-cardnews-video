@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title PhoneSpot - Full Producer Setup (run once per PC)

rem Makes THIS PC a standalone full producer: cardnews + video, all local.
rem Run this AFTER the repo is on the PC (git clone). It is inside the repo.

set "ROOT=%~dp0.."
pushd "%ROOT%" >nul

rem ---- pick python: prefer panel runtime venv, else system ----
set "PY="
if exist "%ROOT%\.phonespot_runtime\Scripts\python.exe" set "PY=%ROOT%\.phonespot_runtime\Scripts\python.exe"
rem MS Store "python" stub passes "where python" but cannot run; verify by running it.
if not defined PY for /f "tokens=2 delims=. " %%V in ('python --version 2^>^&1') do if "%%V"=="3" set "PY=python"
if not defined PY (
  echo [ERROR] Python 3.10+ not found. Install Python first, then re-run.
  popd & pause & exit /b 1
)
where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js not found. Install Node.js LTS first, then re-run.
  popd & pause & exit /b 1
)
echo Using Python: %PY%

echo.
echo ===== 1/5: npm install (Remotion) =====
pushd "%ROOT%\shorts" >nul
call npm install --no-audit --no-fund
popd >nul

echo.
echo ===== 2/5: python deps (render + cardnews + embedding) =====
"%PY%" -m pip install --use-deprecated=legacy-certs --upgrade edge-tts mutagen pillow requests playwright flask fastembed numpy socksio
if errorlevel 1 (
  echo [WARN] legacy-certs failed ^(older pip?^) - retry plain
  "%PY%" -m pip install --upgrade edge-tts mutagen pillow requests playwright flask fastembed numpy socksio
)
if errorlevel 1 (
  echo [WARN] normal install failed - retry with --user
  "%PY%" -m pip install --user --upgrade edge-tts mutagen pillow requests playwright flask fastembed numpy socksio
)

rem optional: whisper forced-alignment for Supertone precise sync (non-fatal)
"%PY%" -m pip install --use-deprecated=legacy-certs --upgrade faster-whisper
if errorlevel 1 "%PY%" -m pip install --upgrade faster-whisper

echo.
echo ===== 3/5: playwright chromium =====
set "PLAYWRIGHT_BROWSERS_PATH=%ROOT%\.playwright"
"%PY%" -m playwright install chromium

echo ===== 3-1/5: Remotion browser (Chrome Headless Shell) =====
pushd "%ROOT%\shorts" >nul
call npx remotion browser ensure
popd >nul

echo.
echo ===== 4/5: embedding models (text + CLIP image, ~1GB once) =====
"%PY%" "%ROOT%\shorts\scripts\codex_illust_embed.py" selftest
"%PY%" "%ROOT%\shorts\scripts\codex_image_embed.py" selftest

echo.
echo ===== 5/5: verify =====
"%PY%" "%ROOT%\shorts\scripts\codex_producer_check.py"
set "RC=%ERRORLEVEL%"

popd >nul
echo.
if "%RC%"=="0" (
  echo [DONE] This PC is ready as a standalone producer.
  echo   - Run 00_PHONE_SPOT_PANEL.bat to start.
  echo   - For card creation: cardnews\webui\start.bat
  echo   - To share the illustration library, set PHONESPOT_LIBRARY_SHARE and use the panel button.
) else (
  echo [DONE with FAILs] Install the [FAIL] items above, then run this again.
)
echo.
pause
