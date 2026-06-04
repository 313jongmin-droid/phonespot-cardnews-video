@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Apply Current Remotion Baseline
echo ============================================================
echo.
echo Step 1/12: Install Korean caption and fixed CTA guard
python APPLY_CODEX_KOREAN_CAPTION_GUARD.py
if errorlevel 1 (
  echo.
  echo [ERROR] Korean caption and CTA guard install failed.
  pause
  exit /b 1
)
echo.
echo Step 2/12: Install source-image once guard
python APPLY_CODEX_SOURCE_IMAGE_ONCE_GUARD.py
if errorlevel 1 (
  echo.
  echo [ERROR] Source-image once guard install failed.
  pause
  exit /b 1
)
echo.
echo Step 3/12: Install one-folder Codex video desk
python APPLY_CODEX_VIDEO_DESK.py
if errorlevel 1 (
  echo.
  echo [ERROR] Codex video desk install failed.
  pause
  exit /b 1
)
echo.
echo Step 4/12: Install concise Codex baseline guide
python APPLY_CODEX_GUIDE_BASELINE.py
if errorlevel 1 (
  echo.
  echo [ERROR] Codex baseline guide install failed.
  pause
  exit /b 1
)
echo.
echo Step 5/12: Install master non-regression video guide
python APPLY_CODEX_MASTER_VIDEO_GUIDE.py
if errorlevel 1 (
  echo.
  echo [ERROR] Master video guide install failed.
  pause
  exit /b 1
)
echo.
echo Step 6/12: Install clean UTF-8 illustration scout
python APPLY_CODEX_CLEAN_ILLUSTRATION_SCOUT.py
if errorlevel 1 (
  echo.
  echo [ERROR] Clean UTF-8 illustration scout install failed.
  pause
  exit /b 1
)
echo.
echo Step 7/12: Install two-click GPT Plus illustration desk
python APPLY_CODEX_FAST_ILLUSTRATION_DESK.py
if errorlevel 1 (
  echo.
  echo [ERROR] Fast GPT Plus illustration desk install failed.
  pause
  exit /b 1
)
echo.
echo Step 8/12: Hide sentence periods in screen captions
python APPLY_CODEX_HIDE_CAPTION_PERIODS.py
if errorlevel 1 (
  echo.
  echo [ERROR] Caption period guard install failed.
  pause
  exit /b 1
)
echo.
echo Step 9/12: Disable inferred inline caption highlights
python APPLY_CODEX_DISABLE_CAPTION_HIGHLIGHT.py
if errorlevel 1 (
  echo.
  echo [ERROR] Caption-highlight disable patch failed.
  pause
  exit /b 1
)
echo.
echo Step 10/12: Install TTS-caption lockstep
python APPLY_CODEX_TTS_CAPTION_LOCKSTEP.py
if errorlevel 1 (
  echo.
  echo [ERROR] TTS-caption lockstep install failed.
  pause
  exit /b 1
)
echo.
echo Step 11/12: Install fixed caption font and independent visual rhythm
python APPLY_CODEX_FIXED_CAPTION_RHYTHM.py
if errorlevel 1 (
  echo.
  echo [ERROR] Fixed-caption rhythm patch failed.
  pause
  exit /b 1
)
echo.
echo Step 12/12: Install single-folder result package V2
python APPLY_CODEX_RESULTS_PACKAGE_V2.py
if errorlevel 1 (
  echo.
  echo [ERROR] Result package V2 install failed.
  pause
  exit /b 1
)
echo.
echo [OK] Current Codex Remotion baseline applied.
echo.
pause
