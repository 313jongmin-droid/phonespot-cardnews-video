@echo off
chcp 65001 >nul
setlocal
title PhoneSpot - illustration library sync
set "ROOT=%~dp0.."
set "PY=%ROOT%\.phonespot_runtime\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo ============================================================
echo  Illustration library sync (two-way additive merge)
echo ============================================================
echo  Hub path: env PHONESPOT_LIBRARY_SHARE  or
echo            file shorts\config\library_share_path.txt
echo  (preview only: pass --dry-run)
echo.
"%PY%" "%ROOT%\shorts\scripts\codex_library_sync.py" %*
echo.
pause
