@echo off
chcp 65001 >nul
title PhoneSpot panel - pin to taskbar
echo Creating PhoneSpot panel shortcut and pinning to taskbar...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0MAINTENANCE\pin_panel.ps1"
echo.
pause
