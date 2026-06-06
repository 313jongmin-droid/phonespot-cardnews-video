@echo off
setlocal
chcp 65001 >nul
title PhoneSpot - Embedding Setup (run once per PC)

rem Installs the free local embedding engine (fastembed + multilingual MiniLM).
rem First run downloads the model (~220MB), then works offline.
rem If it fails, the pipeline still works in lexical fallback mode.

pushd "%~dp0" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Cannot enter shorts folder: %~dp0
  pause
  exit /b 1
)

rem ---- detect python command: python -> py -3 -> python3 ----
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY ( where py >nul 2>nul && set "PY=py -3" )
if not defined PY ( where python3 >nul 2>nul && set "PY=python3" )
if not defined PY (
  echo [ERROR] Python not found. Install Python and run again.
  popd
  pause
  exit /b 1
)
echo Using Python: %PY%

echo.
echo ===== 1/3: install fastembed / numpy / socksio =====
%PY% -m pip install --upgrade fastembed numpy socksio
if errorlevel 1 (
  echo [WARN] normal install failed - retry with --user
  %PY% -m pip install --user --upgrade fastembed numpy socksio
)

echo.
echo ===== 2/3: download model + self-test =====
echo (first run downloads the model, may take 1-2 minutes)
%PY% scripts\codex_illust_embed.py selftest

echo.
echo ===== 3/3: final check =====
%PY% scripts\codex_illust_embed.py check
if errorlevel 1 (
  echo.
  echo [RESULT] Embedding NOT available ^(FALSE^).
  echo          - Check internet/proxy, then run this file again.
  echo          - Pipeline still works in lexical fallback.
) else (
  echo.
  echo [RESULT] Embedding ENABLED ^(TRUE^).
  echo          Press panel button "1" again - concepts/matching now use meaning.
)

popd
echo.
pause
