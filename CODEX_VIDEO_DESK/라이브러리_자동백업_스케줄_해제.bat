@echo off
chcp 65001 >nul
schtasks /delete /tn "PhoneSpot Library Backup" /f
echo.
echo [OK] 라이브러리 자동 백업 스케줄을 해제했습니다(또는 원래 없었음).
pause
