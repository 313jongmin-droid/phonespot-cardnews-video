@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
rem run_banner.bat <slug> : build banner_script + render BannerAd composition
rem banner track (STEP2, 2026-06-19). casual/promo untouched.
if "%~1"=="" (
  echo usage: run_banner.bat ^<slug^>
  exit /b 1
)
set "SLUG=%~1"
cd /d "%~dp0"
set "PY=..\.phonespot_runtime\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo [banner] build script + tts ...
"%PY%" scripts\build_banner.py %SLUG%
if errorlevel 1 (
  echo [banner] build failed
  exit /b 1
)

set "RESULTDIR=..\CODEX_VIDEO_DESK\RESULTS\%SLUG%_banner"
if not exist "%RESULTDIR%" mkdir "%RESULTDIR%"
set "OUT=%RESULTDIR%\%SLUG%_banner.mp4"

echo [banner] render BannerAd ...
call node scripts\render_remotion_fast.mjs BannerAd "%OUT%"
"%PY%" scripts\build_ad_copy.py %SLUG%
echo [banner] done: %OUT%
endlocal
