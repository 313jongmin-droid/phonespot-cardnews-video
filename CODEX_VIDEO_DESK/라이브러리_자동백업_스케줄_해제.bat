@echo off
chcp 65001 >nul
schtasks /delete /tn "PhoneSpot Library Backup" /f
echo.
echo [OK] daily library backup schedule removed (or was not present).
pause
