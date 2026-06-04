@echo off
setlocal
chcp 65001 >nul
title PhoneSpot Codex - Assistant PC Write Access Check
cd /d "%~dp0"
python CHECK_ASSISTANT_PC_WRITE_ACCESS.py
echo.
pause
