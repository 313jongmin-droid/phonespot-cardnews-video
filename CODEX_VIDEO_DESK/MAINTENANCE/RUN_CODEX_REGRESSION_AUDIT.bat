@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo  PhoneSpot Codex - Regression Audit
echo ============================================================
py CODEX_REGRESSION_AUDIT.py %*
echo.
pause
