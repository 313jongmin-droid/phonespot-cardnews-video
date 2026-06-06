@echo off
chcp 65001 >nul
title 폰스팟 패널 - 작업표시줄 바로가기 만들기
echo 폰스팟 패널 바로가기를 만들고 작업표시줄에 고정합니다...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0MAINTENANCE\pin_panel.ps1"
echo.
pause
