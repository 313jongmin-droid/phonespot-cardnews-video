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
echo  e.g.  G:\My Drive\PhoneSp