@echo off
chcp 65001 >nul
set "HERE=%~dp0"
del "%HERE%TEMP\panel\auto_update.on" >nul 2>&1
echo [OK] auto-update OFF
echo  - Panel will no longer run git pull on start.
pause
