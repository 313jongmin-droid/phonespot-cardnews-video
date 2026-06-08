@echo off
chcp 65001 >nul
rem Set this PC's illustration share-hub path (once per PC).
rem Hub = a folder inside a cloud sync folder (Google Drive / Dropbox).
rem Point each PC at the same cloud folder (local path may differ per PC).
setlocal
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "CFG=%ROOT%\shorts\config\library_share_path.txt"

echo ============================================================
echo  Illustration share-hub path setup
echo ============================================================

rem 1) auto-detect (Google Drive desktop) first
set "PYDET=%ROOT%\.phonespot_runtime\Scripts\python.exe"
if not exist "%PYDET%" set "PYDET=python"
echo [auto] trying to detect Google Drive hub folder...
"%PYDET%" "%ROOT%\shorts\scripts\codex_detect_drive_hub.py"
if not errorlevel 1 (
  echo.
  echo [OK] auto-detected and saved. Next: panel "Manage > library sync".
  pause
  exit /b 0
)

echo.
echo  Auto-detect failed. Enter the path manually.
echo  e.g.  G:\My Drive\PhoneSpot_Library   /   G:\내 드라이브\PhoneSpot_Library
set /p HUB=Hub folder path (Enter to cancel):
if "%HUB%"=="" ( echo canceled. & pause & exit /b 1 )

if not exist "%HUB%" (
  echo [create] %HUB%
  mkdir "%HUB%" 2>nul
)
if not exist "%ROOT%\shorts\config" mkdir "%ROOT%\shorts\config" 2>nul
> "%CFG%" echo %HUB%

echo.
echo [OK] saved: %CFG%
echo       hub: %HUB%
echo.
echo Next: panel "Manage > library sync" to merge both ways.
pause
