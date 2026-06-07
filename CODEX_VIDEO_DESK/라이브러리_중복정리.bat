@echo off
chcp 65001 >nul
setlocal
title PhoneSpot - library dedup
set "ROOT=%~dp0.."
set "PY=%ROOT%\.phonespot_runtime\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo ============================================================
echo  Library dedup
echo ============================================================
echo  no args  = report only (read-only, safe).
echo  real cleanup (delete+merge) = pass arg  --apply
echo  threshold: set PHONESPOT_DEDUP_SIM=0.90  (lower = groups more)
echo  * recommended: run library sync (backup) before --apply.
echo.
"%PY%" "%ROOT%\shorts\scripts\codex_library_dedup.py" %*
echo.
pause
