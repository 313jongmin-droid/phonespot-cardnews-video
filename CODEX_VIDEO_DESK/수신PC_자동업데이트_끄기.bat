@echo off
chcp 65001 >nul
set "HERE=%~dp0"
del "%HERE%TEMP\panel\auto_update.on" >nul 2>&1
echo [OK] 자동 업데이트 OFF
echo  - 이제 패널 시작 시 git pull 을 수행하지 않습니다.
pause
