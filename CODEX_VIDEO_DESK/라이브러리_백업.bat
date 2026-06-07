@echo off
chcp 65001 >nul
setlocal
title PhoneSpot - illustration library backup
set "ROOT=%~dp0.."
set "PY=%ROOT%\.phonespot_runtime\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo ============================================================
echo  Illustration library backup (timestamp snapshot, rotation)
echo ============================================================
echo  location: env PHONESPOT_LIBRARY_BACKUP (else <repo parent>\phonespot_library_backups)
echo  keep    : PHONESPOT_LIBRARY_BACKUP_KEEP (default 10)
echo  if PHONESPOT_LIBRARY_SHARE is set, the hub is backed up too.
echo.
"%PY%" "%ROOT%\shorts\scripts\codex_library_backup.py"
echo.
pause
